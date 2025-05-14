import re
import sys
import logging
from typing import Optional, TypedDict, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator

from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.llm_factory import get_llm_provider
from app.utils.streamlit_output import output

from langgraph.graph import StateGraph, END

def init_llm(llm_provider):
    """
    Deve ser chamado por app.py logo após escolher o LLM.
    Atualiza globalmente llm, os chains e recompila o grafo.
    """
    global llm, intent_chain, extraction_chain, compiled_graph
    llm = llm_provider

    intent_chain = intent_prompt | llm.with_structured_output(IntentOutput)
    extraction_chain = extraction_prompt | llm.with_structured_output(PartialUserData)

    # recompila o StateGraph para usar os chains atualizados
    compiled_graph = graph.compile()

    logging.getLogger(__name__).info(f"[AGENT] Grafo de login inicializado com {llm_provider}")

# ──────────────────────────────────────────────────────────────────────────────
# 📋 Logging Setup
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)

log_user = logging.getLogger("user")
log_agent = logging.getLogger("agent")
log_tool = logging.getLogger("tool")
log_sys = logging.getLogger("system")

# ──────────────────────────────────────────────────────────────────────────────
# ✅ Data Model
# ──────────────────────────────────────────────────────────────────────────────
class UserData(BaseModel):
    cpf: str = Field(description="Brazilian CPF in digits or ###.###.###-## format")
    cartao_saude: str = Field(description="Health card in format ABC123456789")

    @field_validator("cartao_saude")
    @classmethod
    def validate_cartao_format(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}\d{9}$", v.upper()):
            raise ValueError("Cartão de saúde deve estar no formato ABC123456789")
        return v.upper()

    @field_validator("cpf")
    @classmethod
    def validate_cpf_format(cls, v: str) -> str:
        digits = re.sub(r'\D', '', v)
        if len(digits) != 11:
            raise ValueError("CPF must contain 11 digits")
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class PartialUserData(BaseModel):
    cpf: Optional[str] = None
    cartao_saude: Optional[str] = None

class GraphState(TypedDict):
    input: str
    data: dict
    confirmed: bool
    intent: Optional[Literal["update", "list", "provide", "invalid"]]

class IntentOutput(BaseModel):
    intent: Literal["update", "list", "provide", "invalid"]

# ──────────────────────────────────────────────────────────────────────────────
# 🤖 Tools
# ──────────────────────────────────────────────────────────────────────────────
@tool(description="List the current data collected from the user.")
def list_data(data: dict) -> str:
    log_tool.info("[TOOL] list_data called")
    if not data:
        return "📋 Nenhum dado foi coletado ainda."
    return "\n".join(f"- {k}: {v}" for k, v in data.items())

@tool(description="Update a specific field in the user data (cpf or cartao_saude).")
def update_data(data: dict, field: str, value: str) -> str:
    log_tool.info(f"[TOOL] update_data called for {field} -> {value}")
    try:
        updated = {**data, field: value}
        confirmed = UserData(**updated)
        return f"Updated {field} to {confirmed.dict()[field]}."
    except (ValidationError, ValueError):
        return f"Invalid {field} format."

# ──────────────────────────────────────────────────────────────────────────────
# 🔮 LLM Setup
# ──────────────────────────────────────────────────────────────────────────────


intent_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Classifique a intenção do usuário como uma das seguintes:\n"
     "- 'provide': quando ele fornece CPF ou número do cartão de saúde\n"
     "- 'update': quando quer alterar valores\n"
     "- 'list': quando quer saber o que já foi coletado\n"
     "- 'invalid': se não conseguir identificar a intenção.\n"
     "Sempre classifique de forma conservadora."),
    ("human", "{input}")
])

extraction_prompt = ChatPromptTemplate.from_messages([
    ("system", "Extraia CPF e número do cartão de saúde (formato ABC123456789) da mensagem."),
    ("human", "{input}")
])

# ──────────────────────────────────────────────────────────────────────────────
# 🔁 LangGraph Nodes
# ──────────────────────────────────────────────────────────────────────────────
def extract_info(state: GraphState) -> GraphState:
    log_agent.info(f"[AGENT] Extracting data from: {state['input']}")
    partial = extraction_chain.invoke({"input": state["input"]})
    state["data"].update({k: v for k, v in partial.model_dump().items() if v is not None})
    return state

def detect_intent(state: GraphState) -> GraphState:
    log_agent.info(f"[AGENT] Detecting intent for: {state['input']}")
    intent_result = intent_chain.invoke({"input": state["input"]})
    state["intent"] = intent_result.intent
    log_agent.info(f"[AGENT] Intent Detected: {state['intent']}")
    return state

def route(state: GraphState) -> str:
    intent = state["intent"]
    return intent if intent in {"update", "list", "provide"} else "invalid"

def handle_update(state: GraphState) -> GraphState:
    if "cpf" in state["input"]:
        field, val = "cpf", state["input"].split()[-1]
    elif "cartao_saude" in state["input"]:
        field, val = "cartao_saude", state["input"].split()[-1]
    else:
        log_tool.warning("Could not extract update field.")
        return state
    response = update_data(state["data"], field=field, value=val)
    log_tool.info(f"[TOOL] {response}")
    return state

def handle_list(state: GraphState) -> GraphState:
    data = state["data"]
    summary = list_data.invoke({"data": data})
    log_tool.info(f"[TOOL] {summary}")
    output(summary)
    state["input"] = ""
    state["intent"] = None
    return state

def finish_or_continue(state: GraphState) -> str:
    if "cpf" in state["data"] and "cartao_saude" in state["data"]:
        return "confirm"
    return "input"

def handle_invalid(state: GraphState) -> GraphState:
    output("🤖 Desculpe, não entendi. Você pode informar seu CPF ou ID?")
    log_agent.warning("[AGENT] Entrada inválida.")
    return state

def handle_provide(state: GraphState) -> GraphState:
    data = state["data"]
    log_agent.info("[AGENT] Dados parciais coletados: %s", data)

    if "cpf" in data and "cartao_saude" in data:
        output("🎉 Pronto! Já tenho todos os dados.")
    elif "cpf" in data:
        output("👍 Já recebi seu CPF. Agora preciso do seu *cartão de saúde* (formato ABC123456789).")
    elif "cartao_saude" in data:
        output("👍 Já recebi seu *cartão de saúde*. Agora preciso do seu CPF.")
    else:
        output("📋 Vamos continuar. Pode me passar seu CPF e cartão de saúde.")

    state["input"] = ""
    return state

def handle_confirm(state: GraphState) -> GraphState:
    log_agent.info("[AGENT] Confirmação automática ativada.")
    #output("\n📋 Dados coletados automaticamente:")
    #output(str(UserData(**state["data"]).model_dump_json(indent=2)))
    output("✅ Todos os dados foram coletados corretamente.")
    state["confirmed"] = True
    return state

# ──────────────────────────────────────────────────────────────────────────────
# 🧠 LangGraph Assembly
# ──────────────────────────────────────────────────────────────────────────────
graph = StateGraph(GraphState)
graph.add_node("extract", extract_info)
graph.add_node("detect_intent", detect_intent)
graph.add_node("update", handle_update)
graph.add_node("list", handle_list)
graph.add_node("provide", handle_provide)
graph.add_node("invalid", handle_invalid)
graph.add_node("confirm", handle_confirm)

graph.set_entry_point("extract")
graph.add_edge("extract", "detect_intent")
graph.add_conditional_edges("detect_intent", route)
graph.add_edge("update", "extract")
graph.add_edge("list", "provide")
graph.add_conditional_edges("provide", finish_or_continue)
graph.add_conditional_edges("confirm", lambda state: END if state.get("confirmed") else "extract")

compiled_graph = graph.compile()

# ──────────────────────────────────────────────────────────────────────────────
# 🚀 Entry Point
# ──────────────────────────────────────────────────────────────────────────────
def run():
    log_sys.info("[SYSTEM] Starting LangGraph Chat Agent.")
    output("🤖 Olá! Por favor, informe seu CPF e número do cartão de saúde (formato ABC123456789).")
    state: GraphState = {"input": "", "data": {}, "intent": None, "confirmed": False}
    attempts = 0
    MAX_ATTEMPTS = 5

    while True:
        if attempts >= MAX_ATTEMPTS:
            output("⚠️ Muitas entradas inválidas. Encerrando a conversa.")
            break

        if state.get("confirmed"):
            log_agent.info("[AGENT] Confirmação feita. Finalizando.")
            output("✅ Dados finais:", UserData(**state["data"]).model_dump_json(indent=2))
            return UserData(**state["data"]).model_dump_json(indent=2)

        try:
            if not state["input"]:
                user_input = input("Você: ").strip()
                if not user_input:
                    continue
                log_user.info(f"[USER] {user_input}")
                state["input"] = user_input

            state = compiled_graph.invoke(state)

            if state.get("intent") == "invalid":
                attempts += 1
            else:
                attempts = 0

            if state.get("intent") in ["provide", "update", "list"]:
                state["input"] = ""

        except KeyboardInterrupt:
            output("\n[SYSTEM] Encerrando.")
            sys.exit(0)

if __name__ == "__main__":
    run()
