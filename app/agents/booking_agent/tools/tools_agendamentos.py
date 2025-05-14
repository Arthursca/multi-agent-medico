import os
import logging
import psycopg2
from langchain_core.tools import Tool, StructuredTool
from app.agents.booking_agent.tools.rag_agendamento import agent, QueryState
import asyncio

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PACIENTE_ID = os.getenv("PACIENTE_ID", "1")


def db_connection():
    """Estabelece conexão com o banco de dados PostgreSQL usando variáveis de ambiente."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=os.getenv("POSTGRES_DB", "agendamento_paciente"),
        user=os.getenv("POSTGRES_USER", "rag"),
        password=os.getenv("POSTGRES_PASS", "123456")
    )

def _listar_agendamentos(input: str = "") -> str:
    logger.info(f"Listando todos os agendamentos do paciente ID {PACIENTE_ID}")
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, medico, especializacao, data_hora, status "
            "FROM agendamentos WHERE paciente_id = %s AND status = 'agendada' ORDER BY data_hora",
            (PACIENTE_ID,)
        )
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "Nenhum agendamento encontrado."
        resultado = "Agendamentos do paciente:\n"
        for (aid, medico, esp, data_hora, status) in rows:
            data_hora_str = data_hora if isinstance(data_hora, str) else data_hora.strftime("%Y-%m-%d %H:%M")
            resultado += f"{aid}: Dr(a). {medico} - {esp} em {data_hora_str} ({status})\n"
        return resultado.strip()
    except Exception as e:
        logger.error(f"Erro ao listar agendamentos: {e}")
        return f"Erro ao listar agendamentos: {str(e)}"

def _cancelar_agendamento(agendamento_id: int) -> str:
    logger.info(f"Tentando cancelar agendamento ID {agendamento_id} do paciente {PACIENTE_ID}")
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE agendamentos SET status = 'cancelada' "
            "WHERE id = %s AND paciente_id = %s AND status = 'agendada'",
            (agendamento_id, PACIENTE_ID)
        )
        if cur.rowcount == 0:
            conn.close()
            return "Nenhum agendamento ativo com esse ID foi encontrado."
        conn.commit()
        conn.close()
        return "Agendamento cancelado com sucesso."
    except Exception as e:
        logger.error(f"Erro ao cancelar agendamento ID {agendamento_id}: {e}")
        return f"Erro ao cancelar agendamento: {str(e)}"

def _agendar_consulta(medico: str, especializacao: str, data_hora: str) -> str:
    logger.info(f"Tentando agendar consulta para paciente {PACIENTE_ID} com Dr(a). {medico}, {especializacao} em {data_hora}")
    try:
        conn = db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM agendamentos "
            "WHERE paciente_id = %s AND status = 'agendada' AND data_hora = %s",
            (PACIENTE_ID, data_hora)
        )
        if cur.fetchone():
            conn.close()
            return "Conflito: Já existe um agendamento ativo nesse horário."
        cur.execute(
            "INSERT INTO agendamentos (paciente_id, medico, especializacao, data_hora, status) "
            "VALUES (%s, %s, %s, %s, 'agendada')",
            (PACIENTE_ID, medico, especializacao, data_hora)
        )
        conn.commit()
        conn.close()
        return "Nova consulta marcada com sucesso."
    except Exception as e:
        logger.error(f"Erro ao agendar consulta: {e}")
        return f"Erro ao agendar consulta: {str(e)}"

def _listar_medicos(cidade: str, especialidade: str) -> str:
    prompt = f"Quero agendar com um especialista em {especialidade}"
    st = QueryState(prompt=prompt, cidade=cidade)

    # Executa o agente LangGraph RAG de forma síncrona
    raw_result = asyncio.run(agent.ainvoke(st))

    # Convertendo o resultado para objeto QueryState
    result_state = QueryState(**raw_result)

    return result_state.reply or "Nenhuma resposta encontrada."

# 🔧 Registros como ferramentas LangChain (com descrição)
listar_agendamentos = Tool.from_function(
    name="listar_agendamentos",
    func=_listar_agendamentos,
    description="Lista todos os agendamentos do paciente, incluindo os cancelados."
)

cancelar_agendamento = Tool.from_function(
    name="cancelar_agendamento",
    func=_cancelar_agendamento,
    description="Cancela um agendamento ativo. Requer o ID do agendamento.",
)

agendar_consulta = StructuredTool.from_function(
    name="agendar_consulta",
    func=_agendar_consulta,
    description="Agenda uma nova consulta...",
)

listar_medicos = StructuredTool.from_function(
    name="listar_medicos",
    description="Busca médicos disponíveis por cidade e especialidade. Ex: cidade=sao-paulo, especialidade=psicologo",
    func=_listar_medicos,
)

