import re
import logging
from datetime import datetime, date, time
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError, field_validator

# Ferramentas importadas do arquivo refatorado
from app.agents.booking_agent.tools.tools_agendamentos import listar_agendamentos, cancelar_agendamento, agendar_consulta, listar_medicos

# Configurar log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DadosAgendamento(BaseModel):
    medico: str
    especializacao: str
    data: date
    hora: time

    @field_validator("data")
    def data_futura(cls, v):
        if v < date.today():
            raise ValueError("A data da consulta não pode estar no passado.")
        return v


def identificar_intent(msg: str) -> str:
    msg = msg.strip().lower()
    if re.search(r"\bagendar\b", msg) or re.search(r"\bmarcar\b", msg):
        return "agendar"
    if re.search(r"\bcancelar\b", msg):
        return "cancelar"
    if re.search(r"\blistar\b", msg) or re.search(r"\bmostrar\b", msg) or re.search(r"\bver\b", msg):
        return "listar"


    return "desconhecido"


class AgenteAgendamentos:
    def __init__(self):
        self.estado: Optional[str] = None
        self.dados_temp: Dict[str, Any] = {}
        self.agendamento_pendente: Optional[DadosAgendamento] = None

    def processar_mensagem(self, mensagem: str) -> str:
        logger.info(f"Mensagem recebida: {mensagem}")
        mensagem = mensagem.strip()

        if mensagem.lower().startswith("listar medicos"):
            partes = mensagem.split()
            if len(partes) < 4:
                return "Formato esperado: listar medicos <especialidade> <cidade> \nExemplo: /listar medicos psicologo sao-paulo"
            _, _, especialidade, cidade = partes[:4]
            try:
                resposta = listar_medicos.invoke({
                    "cidade": cidade.lower(),
                    "especialidade": especialidade.lower()
                })
                return resposta
            except Exception as e:
                return f"Erro ao buscar médicos: {e}"


        # Cancelamento de fluxo
        if mensagem.lower() in ["cancelar", "cancelar processo", "cancelar agendamento", "parar", "desistir"]:
            if self.estado in ["agendando", "confirmando_agendamento"]:
                self.estado = None
                self.dados_temp.clear()
                return "Agendamento cancelado pelo usuário. Nenhuma consulta foi marcada."
            if self.estado == "cancelando":
                self.estado = None
                self.dados_temp.clear()
                return "Operação de cancelamento cancelada pelo usuário."

        if self.estado is None:
            intent = identificar_intent(mensagem)
            logger.info(f"Intenção identificada: {intent}")

            if intent == "agendar":
                self.estado = "agendando"
                self.dados_temp.clear()
                return "Claro! Qual o nome do médico?"
            elif intent == "cancelar":
                resultado = listar_agendamentos.invoke("cancelar")
                agendamentos_ativos = [linha for linha in resultado.splitlines() if linha.endswith("(agendada)")]
                if not agendamentos_ativos:
                    return "Você não tem agendamentos ativos no momento."
                self.estado = "cancelando"
                self.dados_temp["ativos_ids"] = [int(l.split(":")[0]) for l in agendamentos_ativos]
                return "Agendamentos ativos:\n" + "\n".join(agendamentos_ativos) + "\nQual ID deseja cancelar?"
            elif intent == "listar":
                return listar_agendamentos.invoke("listar")

            else:
                return "Desculpe, não entendi. Deseja listar, cancelar ou agendar?"

        if self.estado == "agendando":
            if "medico" not in self.dados_temp:
                self.dados_temp["medico"] = mensagem
                return "Qual a especialização do(a) médico(a)?"
            elif "especializacao" not in self.dados_temp:
                self.dados_temp["especializacao"] = mensagem
                return "Informe a data da consulta (AAAA-MM-DD):"
            elif "data" not in self.dados_temp:
                try:
                    self.dados_temp["data"] = datetime.strptime(mensagem, "%Y-%m-%d").date()
                    return "Agora informe o horário (HH:MM):"
                except ValueError:
                    return "Data inválida. Use o formato AAAA-MM-DD (ex: 2025-12-31):"
            elif "hora" not in self.dados_temp:
                try:
                    self.dados_temp["hora"] = datetime.strptime(mensagem, "%H:%M").time()
                except ValueError:
                    return "Hora inválida. Use o formato HH:MM (ex: 14:30):"

                try:
                    dados = DadosAgendamento(**self.dados_temp)
                except ValidationError as e:
                    msgs = "\n".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
                    self.dados_temp.pop("../health_plan_agent/tools/rag/data", None)
                    self.dados_temp.pop("hora", None)
                    return f"Dados inválidos:\n{msgs}\nInforme uma nova data (AAAA-MM-DD):"

                data_hora_str = datetime.combine(dados.data, dados.hora).strftime("%Y-%m-%d %H:%M")
                resultado = agendar_consulta.invoke({
                    "medico": dados.medico,
                    "especializacao": dados.especializacao,
                    "data_hora": data_hora_str
                })

                if "Conflito" in resultado:
                    self.estado = None
                    self.dados_temp.clear()
                    return f"{resultado}\nTente novamente com outro horário."

                self.agendamento_pendente = dados
                self.estado = "confirmando_agendamento"
                return (f"Confirmar agendamento com Dr(a). {dados.medico} - {dados.especializacao} em "
                        f"{dados.data.strftime('%d/%m/%Y')} às {dados.hora.strftime('%H:%M')}? (sim/não)")

        if self.estado == "confirmando_agendamento":
            if mensagem.lower() in ["sim", "s", "yes", "y"]:
                dados = self.agendamento_pendente
                data_hora_str = datetime.combine(dados.data, dados.hora).strftime("%Y-%m-%d %H:%M")
                resultado = agendar_consulta.invoke({
                    "medico": dados.medico,
                    "especializacao": dados.especializacao,
                    "data_hora": data_hora_str
                })
                self.estado = None
                self.dados_temp.clear()
                self.agendamento_pendente = None
                return resultado
            else:
                self.estado = None
                self.dados_temp.clear()
                self.agendamento_pendente = None
                return "Agendamento cancelado conforme sua solicitação."

        if self.estado == "cancelando":
            try:
                id_informado = int(mensagem.strip())
            except ValueError:
                return "Informe um número de ID válido."

            if id_informado not in self.dados_temp.get("ativos_ids", []):
                return "ID inválido. Tente novamente ou digite 'cancelar' para sair."

            resultado = cancelar_agendamento.invoke({"agendamento_id": id_informado})
            self.estado = None
            self.dados_temp.clear()
            return resultado

        return "Ocorreu um erro inesperado. Tente novamente."
