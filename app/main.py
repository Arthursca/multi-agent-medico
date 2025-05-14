import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from app.agents.login_agent.agente_login import UserData, log_sys, GraphState, log_agent, log_user, compiled_graph
from app.agents.booking_agent.agente_agendamento import AgenteAgendamentos
from app.agents.health_plan_agent.agent_plano import graph as graph_plano
from app.llm_factory import get_llm_provider


import sys
import logging
import psycopg2

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)




def db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL usando variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "agendamento_paciente"),
        user=os.getenv("POSTGRES_USER", "rag"),
        password=os.getenv("POSTGRES_PASS", "123456")
    )
# Define chave de API para OpenAI (assegure OPENAI_API_KEY no ambiente)

llm = get_llm_provider()
# Inicializa conexão com o banco de dados (SQLite)
conn = db_connection()
cursor = conn.cursor()

def classify_intent(user_message: str) -> str:
    """
    Usa um modelo LLM (LangChain com OpenAI) para classificar a intenção do usuário.
    Retorna: 'plano', 'agendamento', 'sair' ou 'desconhecido'.
    """
    prompt = (
        "Você é um assistente que classifica a intenção do usuário. "
        "Responda APENAS com uma palavra dentre: plano, agendamento, sair, desconhecido.\n"
        "Responda plano quando for uma duvida sobre o plano de saude (Carencia,Serviços disponibilizados, ...) "
        "Responda agendamento caso seja uma query alando algo sobre agendamento (marcar consulta, ver quais medicos disponiveis....)"
        "Responda sair caso ele uqira encerar o chat"
        "Responda desconhecido caso ele não seja nenhuma das opções acima "
        f"Pergunta do usuário: {user_message}\nIntenção:"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        intent = response.content.strip().lower()
        for possible in ["plano", "agendamento", "sair", "desconhecido"]:
            if possible in intent:
                logger.info(f"Intenção classificada: {possible}")
                return possible
    except Exception as e:
        logger.error("Erro ao chamar o LLM para classificação: %s", e)
    logger.info("Intenção classificada: desconhecido (fallback)")
    return "desconhecido"

def executar_fluxo_plano(user_input: str) -> None:
    """
    Executa o agente de planos (RAG via LangChain). Exibe a resposta.
    """
    try:
        # Cria estado inicial com a query do usuário
        initial_state = {"query": user_input}
        result_state = graph_plano.invoke(initial_state)
        resposta = result_state.get("response", "")
        print(f"🤖 {resposta}")
    except Exception as e:
        logger.error("Erro no agente de plano: %s", e)
        print("🤖 Desculpe, ocorreu um erro ao consultar o plano de saúde.")

def executar_fluxo_agendamento() -> None:
    """
    Executa o agente de agendamentos interativamente (como em runagent.py).
    O loop termina quando o usuário digitar 'cancelar' ou similar.
    """
    print(
        "\n🤖 Olá! Sou seu assistente de agendamentos.\n"
        "   • Digite 'listar' para ver seus agendamentos;\n"
        "   • Digite 'agendar' para marcar uma nova consulta;\n"
        "   • Digite 'cancelar' para cancelar uma consulta ativa;\n"
        "   • Digite '/listar medicos <especialidade> <cidade>' para buscar médicos disponíveis;\n"
        "   • Ou digite 'sair' para encerrar o fluxo de agendamentos.\n"
    )
    agente = AgenteAgendamentos()
    try:
        while True:
            user_input = input("Você: ").strip()
            if not user_input:
                continue
            # Palavras que encerram o fluxo de agendamento
            if user_input.lower() in ["cancelar", "sair", "parar", "desistir", "encerrar"]:
                print("🤖 Fluxo de agendamento encerrado. Como mais posso ajudar?")
                break
            resposta = agente.processar_mensagem(user_input)
            print(f"🤖 {resposta}\n")
    except KeyboardInterrupt:
        print("\n👋 Encerrando agendamentos.")

def obter_dados_paciente(cpf: str, user_id: str) -> dict:
    """
    Consulta o paciente no BD usando CPF e user_id.
    Retorna um dicionário com os campos do paciente, ou None se não encontrado.
    """
    try:
        cursor.execute(
            "SELECT * FROM pacientes WHERE cpf = %s AND cartao_saude = %s",
            (cpf, user_id)
        )

        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            paciente = dict(zip(columns, row))
            logger.info("Dados do paciente recuperados: %s", paciente)
            return paciente
        else:
            return None
    except Exception as e:
        logger.error("Erro na consulta SQL: %s", e)
        return None

def solicitar_login() -> tuple:
    """
    Executa o agente de login e extrai CPF e user_id dos dados finais.
    Retorna (cpf, user_id) ou (None, None) em caso de falha.
    """

    log_sys.info("[SYSTEM] Starting LangGraph Chat Agent.")
    print("🤖 Olá! Por favor, informe seu CPF e número do cartão de saúde (formato ABC123456789).")
    state: GraphState = {"input": "", "data": {}, "intent": None, "confirmed": False}
    attempts = 0
    MAX_ATTEMPTS = 5

    while True:
        if attempts >= MAX_ATTEMPTS:
            print("⚠️ Muitas entradas inválidas. Encerrando a conversa.")
            break

        if state.get("confirmed"):
            log_agent.info("[AGENT] Confirmação feita. Finalizando.")
            print("✅ Dados finais:", UserData(**state["data"]).model_dump_json(indent=2))
            data = UserData(**state["data"])

            return data.cpf, data.cartao_saude



        try:
            if not state["input"]:
                user_input = input("Você: ").strip()
                if not user_input:
                    continue
                log_user.info(f"[USER] {user_input}")
                state["input"] = user_input

            # 🧠 Executa o grafo
            state = compiled_graph.invoke(state)

            # 👇 Importante: NÃO limpar a intenção aqui! Isso já é feito nos nodes corretos
            if state.get("intent") == "invalid":
                attempts += 1
            else:
                attempts = 0

            # ⚠️ Mantém o input limpo apenas se necessário
            if state.get("intent") in ["provide", "update", "list"]:
                state["input"] = ""

        except KeyboardInterrupt:
            print("\n[SYSTEM] Encerrando.")
            sys.exit(0)

def main():
    logger.info("Iniciando Assistente de Planos e Agendamentos.")
    try:
        while True:
            # --- Passo 1: Login ---
            cpf, cartao_saude = solicitar_login()
            if not cpf or not cartao_saude:
                continue  # repetir login até sucesso

            # --- Passo 2: Consulta SQL ---
            paciente = obter_dados_paciente(cpf, cartao_saude)
            if not paciente:
                print("🤖 Dados não encontrados para esse CPF e cartao_saude. Tente novamente.")
                continue  # voltar ao login

            # --- Passo 3: Iniciar conversa ---
            print("\n🤖 Login efetuado com sucesso! Você pode me perguntar sobre seu plano de saúde ou agendamentos.")
            print("🤖 (Digite 'sair' para efetuar novo login quando quiser.)")

            # Loop de conversa
            while True:
                user_input = input("Você: ").strip()
                if not user_input:
                    continue

                # --- Passo 4: Classificar intenção ---
                intent = classify_intent(user_input)

                # --- Passo 5: Encaminhar fluxo conforme intenção ---
                if intent == "plano":
                    executar_fluxo_plano(user_input)
                    continue
                elif intent == "agendamento":
                    executar_fluxo_agendamento()
                    continue
                elif intent == "sair":
                    print("🤖 Você solicitou sair. Voltando ao menu de login.")
                    break  # Sai do loop de conversa para novo login
                else:
                    print("🤖 Desculpe, só posso ajudar com planos de saúde ou agendamentos.")
                    continue
            # volta ao início para novo login
    except KeyboardInterrupt:
        print("\n👋 Encerrando a aplicação. Até logo!")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
