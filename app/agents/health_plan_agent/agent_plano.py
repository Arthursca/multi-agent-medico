# agent_rag_router.py

from typing import TypedDict, Literal

from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

from langsmith.run_helpers import traceable
from app.agents.health_plan_agent.tools.rag.pipeline.rag_pipeline import RAGPipeline, init_llm as init_rag_llm

from app.llm_factory import get_llm_provider


class AgentState(TypedDict):
    query: str
    is_relevant: bool
    response: str

# === NÓ 1: Validação de relevância da query ===
validate_prompt = PromptTemplate.from_template(
    """Você é um assistente que decide se uma pergunta é relevante para um sistema de recuperação de informações sobre plano de saúde.
Pergunta: {query}
Responda apenas com "Sim" ou "Não"."""
)

def init_llm(llm_provider):
    """
    Inicializa o LLM a ser usado pelo pipeline RAG.
    Deve ser chamado a partir de app.py após a seleção do LLM.
    """
    global _llm_provider
    _llm_provider = llm_provider
    init_rag_llm(llm_provider)


def validate_query_fn(state: AgentState) -> AgentState:

    llm = _llm_provider or get_llm_provider('openai')
    chain = validate_prompt | llm | StrOutputParser()
    result = chain.invoke({"query": state["query"]})

    return {
        **state,
        "is_relevant": result.strip().lower().startswith("sim")
    }

validate_query: Runnable = RunnableLambda(validate_query_fn)

# === NÓ 2: Executa RAG se relevante ===
@traceable(name="RunRAG")
def run_rag_fn(state: AgentState) -> AgentState:
    pipeline = RAGPipeline()
    resposta = pipeline.run(state["query"])
    return {**state, "response": resposta}

run_rag: Runnable = RunnableLambda(run_rag_fn)

# === NÓ 3: Resposta padrão se não for relevante ===
def no_data_response_fn(state: AgentState) -> AgentState:
    return {
        **state,
        "response": "Desculpe, não encontrei informações relacionadas a essa pergunta na nossa base de dados de planos de saúde."
    }

no_data_response: Runnable = RunnableLambda(no_data_response_fn)

# === Lógica de transição ===
def route_based_on_validation(state: AgentState) -> Literal["run_rag", "no_data"]:
    return "run_rag" if state["is_relevant"] else "no_data"

# === Construção do grafo ===
graph_builder = StateGraph(AgentState)
graph_builder.add_node("validate", validate_query)
graph_builder.add_node("run_rag", run_rag)
graph_builder.add_node("no_data", no_data_response)

graph_builder.set_entry_point("validate")
graph_builder.add_conditional_edges("validate", route_based_on_validation, {
    "run_rag": "run_rag",
    "no_data": "no_data",
})
graph_builder.add_edge("run_rag", END)
graph_builder.add_edge("no_data", END)

graph = graph_builder.compile()

# === Execução do Agente ===
if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    user_query = " ".join(sys.argv[1:]) or "Quais os exames basicos e quais suas carencias maximas??"
    initial_state: AgentState = {"query": user_query}

    result = graph.invoke(initial_state)
    print("Resposta final:", result["response"])
