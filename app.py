import os
import psycopg2
import streamlit as st
import logging

from langchain_core.messages import HumanMessage
import builtins
def streamlit_input(prompt: str = "") -> str:
    key = f"input_{prompt}"
    if key not in st.session_state:
        st.text_input(prompt, key=key, on_change=st.rerun)
        st.stop()
    return st.session_state[key]

builtins.input = streamlit_input   # patch feito aqui

# Registra callback para capturar outputs de agentes
from app.utils.streamlit_output import register_callback, output
register_callback(lambda msg: st.session_state['chat_history'].append({'role': 'assistant', 'content': msg}))

import app.agents.login_agent.agente_login as agent_login
from app.agents.booking_agent.agente_agendamento import AgenteAgendamentos
from app.agents.health_plan_agent.agent_plano import graph as graph_plano
from app.llm_factory import get_llm_provider
from app.agents.health_plan_agent.agent_plano import init_llm as init_plano




# ──────────────────────────────────────────────────────────────────────────────
# 🔧 Configuração de logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
#  Inicialização do LLM e conexão com DB
# ──────────────────────────────────────────────────────────────────────────────
provider = st.sidebar.radio("Selecionar provedor de LLM", ["openai", "claude"], index=0)
llm = get_llm_provider(provider)


init_plano(llm)
agent_login.init_llm(llm)
UserData      = agent_login.UserData
compiled_graph = agent_login.compiled_graph

def db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "pgvector"),
        database=os.getenv("POSTGRES_DB", "agendamento_paciente"),
        user=os.getenv("POSTGRES_USER", "rag"),
        password=os.getenv("POSTGRES_PASS", "123456")
    )


conn = db_connection()
cursor = conn.cursor()

# ──────────────────────────────────────────────────────────────────────────────
# 🎯 Função para classificar intenção no modo principal
# ──────────────────────────────────────────────────────────────────────────────

def classify_intent(user_message: str) -> str:
    prompt = (
        "Você é um assistente que classifica a intenção do usuário. "
        "Responda APENAS com: plano, agendamento, sair ou desconhecido.\n"
        f"Pergunta do usuário: {user_message}\nIntenção:"
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        intent = response.content.strip().lower()
        for option in ["plano", "agendamento", "sair", "desconhecido"]:
            if option in intent:
                logger.info(f"Intenção: {option}")
                return option
    except Exception as e:
        logger.error("Erro na classificação: %s", e)
    return "desconhecido"

# ──────────────────────────────────────────────────────────────────────────────
# 🔎 Consulta paciente
# ──────────────────────────────────────────────────────────────────────────────

def obter_dados_paciente(cpf: str, user_id: str) -> dict:
    try:
        cursor.execute(
            "SELECT * FROM pacientes WHERE cpf = %s AND cartao_saude = %s",
            (cpf, user_id)
        )
        row = cursor.fetchone()
        if row:
            cols = [c[0] for c in cursor.description]
            return dict(zip(cols, row))
    except Exception as e:
        logger.error("Erro SQL: %s", e)
    return None

# ──────────────────────────────────────────────────────────────────────────────
# 🌐 Inicializa estado do Streamlit
# ──────────────────────────────────────────────────────────────────────────────
if 'mode' not in st.session_state:
    st.session_state['mode'] = 'login'

# Estado de login mantém todas as variáveis necessárias para o grafo
if 'login_state' not in st.session_state:
    st.session_state['login_state'] = {
        "input": "",
        "data": {},
        "intent": None,
        "confirmed": False,
        "awaiting_confirmation": False,
    }

if 'login_attempts' not in st.session_state:
    st.session_state['login_attempts'] = 0
if 'cpf' not in st.session_state:
    st.session_state['cpf'] = None
if 'cartao' not in st.session_state:
    st.session_state['cartao'] = None
if 'booking_agent' not in st.session_state:
    st.session_state['booking_agent'] = None
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

# ──────────────────────────────────────────────────────────────────────────────
# ✉️ Mensagem inicial
# ──────────────────────────────────────────────────────────────────────────────
if not st.session_state['chat_history']:
    greeting = " Olá! Por favor, informe seu CPF e número do cartão de saúde (formato ABC123456789)."
    st.session_state['chat_history'].append({'role': 'assistant', 'content': greeting})

# ──────────────────────────────────────────────────────────────────────────────
# 💬 Interface de chat
# ──────────────────────────────────────────────────────────────────────────────
chat_placeholder = st.container()

# Input do usuário
user_input = st.chat_input("Você:")
if user_input:
    st.session_state['chat_history'].append({'role': 'user', 'content': user_input})

    # ------------------------------------------------------------
    # 🔐 Fluxo de LOGIN
    # ------------------------------------------------------------
    if st.session_state['mode'] == 'login':
        # ⚠️ Recupera e atualiza o estado do grafo
        state = st.session_state['login_state']
        state['input'] = user_input
        state = compiled_graph.invoke(state)
        st.session_state['login_state'] = state  # Persiste estado

        # ➡️ Tratamento de respostas inválidas (quando NÃO aguardamos confirmação)
        if state.get('intent') == 'invalid' and not state.get('awaiting_confirmation', False):
            st.session_state['login_attempts'] += 1
            if st.session_state['login_attempts'] >= 5:
                msg = "⚠️ Muitas entradas inválidas. Encerrando."
                st.session_state['chat_history'].append({'role': 'assistant', 'content': msg})
                # Reinicia estado de login completo
                st.session_state['login_state'] = {
                    "input": "",
                    "data": {},
                    "intent": None,
                    "confirmed": False,
                    "awaiting_confirmation": False,
                }
                st.session_state['login_attempts'] = 0

        # ✅ Confirmação positiva: dados completos e corretos
        elif state.get('confirmed'):
            data = UserData(**state['data'])
            st.session_state['cpf'] = data.cpf
            st.session_state['cartao'] = data.cartao_saude
            #st.session_state['chat_history'].append({'role': 'assistant', 'content': f"✅ Dados: {data.model_dump_json()}"})
            paciente = obter_dados_paciente(data.cpf, data.cartao_saude)
            if not paciente:
                st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Dados não encontrados. Tente novamente.'})
                # Reinicia estado de login
                st.session_state['login_state'] = {
                    "input": "",
                    "data": {},
                    "intent": None,
                    "confirmed": False,
                    "awaiting_confirmation": False,
                }
                st.session_state['login_attempts'] = 0
            else:
                st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Login bem-sucedido! Pergunte sobre plano ou agendamento.'})
                st.session_state['mode'] = 'main'
                st.session_state['login_attempts'] = 0  # Reseta tentativas

    # ------------------------------------------------------------
    # 🏠 Fluxo PRINCIPAL
    # ------------------------------------------------------------
    elif st.session_state['mode'] == 'main':
        intent = classify_intent(user_input)
        if intent == 'plano':
            try:
                res = graph_plano.invoke({'query': user_input})
                resp = res.get('response', '')
            except Exception:
                resp = ' Erro ao consultar o plano.'
            st.session_state['chat_history'].append({'role': 'assistant', 'content': f' {resp}'})

        elif intent == 'agendamento':
            st.session_state['booking_agent'] = AgenteAgendamentos()
            st.session_state['mode'] = 'booking'
            intro = (
                " Assistente de agendamentos:\n"
                " • 'listar' para ver agendamentos;\n"
                " • 'agendar' para nova consulta;\n"
                " • 'cancelar' para cancelar;\n"
                " • '/listar medicos <esp> <cid>' para buscar médicos;\n"
                " • 'sair' para voltar."
            )
            st.session_state['chat_history'].append({'role': 'assistant', 'content': intro})

        elif intent == 'sair':
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Voltando ao login.'})
            # Reinicia estados principais
            st.session_state['mode'] = 'login'
            st.session_state['login_state'] = {
                "input": "",
                "data": {},
                "intent": None,
                "confirmed": False,
                "awaiting_confirmation": False,
            }
            st.session_state['login_attempts'] = 0
            st.session_state['cpf'] = None
            st.session_state['cartao'] = None
            st.session_state['booking_agent'] = None
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Informe CPF e cartão.'})

        else:
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Só posso ajudar com plano ou agendamento.'})

    # ------------------------------------------------------------
    # 📅 Fluxo de AGENDAMENTO
    # ------------------------------------------------------------
    elif st.session_state['mode'] == 'booking':
        agent = st.session_state['booking_agent']
        if user_input.lower() in ['cancelar', 'sair', 'parar', 'desistir', 'encerrar']:
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Fim do fluxo de agendamento.'})
            st.session_state['chat_history'].append({'role': 'assistant', 'content': ' Pergunte sobre plano ou agendamento.'})
            st.session_state['mode'] = 'main'
            st.session_state['booking_agent'] = None
        else:
            resp = agent.processar_mensagem(user_input)
            st.session_state['chat_history'].append({'role': 'assistant', 'content': f' {resp}'})

# ──────────────────────────────────────────────────────────────────────────────
# 🖥️ Renderiza todo o chat
# ──────────────────────────────────────────────────────────────────────────────
with chat_placeholder:
    for msg in st.session_state['chat_history']:
        with st.chat_message(msg['role']):
            st.write(msg['content'])
