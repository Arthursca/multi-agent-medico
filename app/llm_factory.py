# pipeline/llm_factory.py

"""
pipeline.llm_factory

Fábrica para seleção e instanciação do cliente de LLM
com base na variável de configuração LLM_PROVIDER.
"""

from typing import Any

from PIL.ImageStat import Global

from app.config import LLM_PROVIDER
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.tracers.langchain import LangChainTracer
import os, uuid
from langsmith import Client


os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ.setdefault("LANGCHAIN_ENDPOINT", "https://api.langsmith.com")
os.environ.setdefault("LANGCHAIN_API_KEY", os.getenv("LANGSMITH_API_KEY", ""))
os.environ["LANGCHAIN_PROJECT"] = "agente-medico"



logger = get_logger(__name__)

_tracer = LangChainTracer(
    project_name="agente-medico",
    client=Client(),
    tags=[f"conversation_id:{uuid.uuid4()}"],
)




def get_llm_provider( provider:str) -> Any:
    """
    Retorna uma instância do cliente de LLM conforme o valor de LLM_PROVIDER.

    Raises:
        ValueError: Se LLM_PROVIDER não corresponder a nenhum provedor suportado.
    """
    model=None
    if provider == "openai":
        model = ChatOpenAI(model="gpt-4o-mini",
                           temperature=0.3,
                           callbacks=[_tracer])
    elif provider == "claude":
        model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.3,
            callbacks=[_tracer])

    return model
