"""
Agente de agendamento médico – versão modificada
Cidade é passada por fora do prompt do usuário.
"""

from __future__ import annotations
import  json, asyncio
from typing import List, Optional


from langgraph.graph import StateGraph, END

from pydantic import BaseModel
from app.llm_factory import get_llm_provider

# ─── configuração de tracing ────────────────────────────────────────────────


# ─── especialidades & cidades suportadas ────────────────────────────────────
ESPECIALIDADES = {"nutrologo", "psiquiatra", "psicologo"}
CIDADES = {"sao-paulo", "recife", "fortaleza"}

# ─── função de scraping (já fornecida) ──────────────────────────────────────
from app.agents.booking_agent.tools.scrape_module import scrape_medicos

# ─── estado do workflow ─────────────────────────────────────────────────────
class QueryState(BaseModel):
    prompt: str
    cidade: Optional[str] = None
    especialidade: Optional[str] = None
    medicos: Optional[List[dict]] = None
    reply: Optional[str] = None

# ─── LLM para parsing de entrada ────────────────────────────────────────────
llm = get_llm_provider('openai')
# Nova versão do schema: extrai apenas a especialidade
FC_SCHEMA = {
    "name": "extrair_especialidade",
    "description": "Extrai apenas a especialidade desejada pelo usuário.",
    "parameters": {
        "type": "object",
        "properties": {
            "especialidade": {"type": "string"},
        },
        "required": ["especialidade"],
    },
}

# ─── nós do grafo ───────────────────────────────────────────────────────────
def parse_input(st: QueryState) -> QueryState:
    """Extrai apenas a especialidade do prompt."""
    resp = llm.invoke(
        [{"role": "user", "content": st.prompt}],
        functions=[FC_SCHEMA],
        function_call="auto",
    )
    if "function_call" in resp.additional_kwargs:
        args = json.loads(resp.additional_kwargs["function_call"]["arguments"])
        st.especialidade = args["especialidade"].lower().strip()
    return st

def validate(st: QueryState) -> QueryState:
    """Valida cidade e especialidade fornecidas."""
    if st.cidade not in CIDADES:
        st.reply = (
            f"Desculpe, ainda não tenho informações para a cidade “{st.cidade}”.\n"
            f"Cidades disponíveis: {', '.join(sorted(CIDADES))}."
        )
    elif st.especialidade not in ESPECIALIDADES:
        st.reply = (
            f"Desculpe, ainda não tenho informações sobre a especialidade "
            f"“{st.especialidade}”.\nEspecialidades disponíveis: "
            f"{', '.join(sorted(ESPECIALIDADES))}."
        )
    return st

def buscar_medicos(st: QueryState) -> QueryState:
    """Executa o scraping de médicos."""
    st.medicos = scrape_medicos(st.cidade, st.especialidade)[:5]
    return st

def format_reply(st: QueryState) -> QueryState:
    """Formata a resposta final ao usuário."""
    if st.reply:
        return st
    if not st.medicos:
        st.reply = (
            f"Nenhum profissional de {st.especialidade.title()} encontrado em "
            f"{st.cidade.replace('-', ' ').title()} com o convênio solicitado."
        )
    else:
        linhas = [
            f"{i+1}. {m['nome']} – {m['endereco']} "
            #f"(CRM {m['crm'] or '—'})"
            for i, m in enumerate(st.medicos)
        ]
        st.reply = (
            f"Eis alguns profissionais de **{st.especialidade.title()}** em "
            f"**{st.cidade.replace('-', ' ').title()}**:\n\n" + "\n".join(linhas)
        )
    return st

# ─── construção do grafo ────────────────────────────────────────────────────
g = StateGraph(QueryState)
g.add_node("PARSE", parse_input)
g.add_node("VALIDATE", validate)
g.add_node("BUSCAR", buscar_medicos)
g.add_node("RESPONDER", format_reply)

g.set_entry_point("PARSE")

g.add_edge("PARSE", "VALIDATE")
g.add_conditional_edges("VALIDATE", lambda s: "RESPONDER" if s.reply else "BUSCAR")
g.add_edge("BUSCAR", "RESPONDER")
g.add_edge("RESPONDER", END)

agent = g.compile()

# ─── interface CLI com entrada separada de cidade ───────────────────────────
async def run_cli() -> None:
    cidade = input("🌆 Informe a cidade (ex: sao-paulo):\n> ").lower().strip()
    prompt = input("👤 Qual especialista você procura?\n> ")
    st = QueryState(prompt=prompt, cidade=cidade)
    st = QueryState.model_validate(await agent.ainvoke(st))
    print("\n🤖 " + (st.reply or "Ocorreu um erro inesperado."))

if __name__ == "__main__":
    asyncio.run(run_cli())
