# utils/callbacks.py

"""
utils/callbacks.py

Configura callbacks para LangChain: logging estruturado e tracing via LangSmith.
"""

from typing import List

from langchain.callbacks.base import BaseCallbackHandler
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.tracers import LangChainTracer
from langsmith import Client  # import necessário para instanciar o tracer
from app.config import LANGSMITH_TRACING, LANGSMITH_API_KEY
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingCallback(BaseCallbackHandler):
    """
    Callback para logar eventos do LangChain com logger JSON estruturado.
    """
    def __init__(self) -> None:
        self.logger = get_logger("langchain.logging")
        super().__init__()

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs) -> None:
        self.logger.info(
            "Chain start",
            extra={"serialized": serialized, "inputs": inputs}
        )

    def on_chain_end(self, outputs: dict, **kwargs) -> None:
        self.logger.info(
            "Chain end",
            extra={"outputs": outputs}
        )

    def on_llm_start(self, serialized: dict, prompts: List[str], **kwargs) -> None:
        self.logger.debug(
            "LLM start",
            extra={"model": serialized.get("model_name"), "prompts": prompts}
        )

    def on_llm_end(self, response: dict, **kwargs) -> None:
        self.logger.debug(
            "LLM end",
            extra={"response": response}
        )

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs) -> None:
        self.logger.debug(
            "Tool start",
            extra={"tool": serialized.get("name"), "input": input_str}
        )

    def on_tool_end(self, output: str, **kwargs) -> None:
        self.logger.debug(
            "Tool end",
            extra={"output": output}
        )


def get_callback_manager() -> CallbackManager:
    """
    Inicializa e retorna o CallbackManager para LangChain,
    incluindo logging estruturado e opcionalmente tracing do LangSmith.

    Returns:
        CallbackManager: gerenciador com handlers configurados.
    """
    # Aqui, LoggingCallback já está definido acima
    callbacks = [LoggingCallback()]

    if LANGSMITH_TRACING:
        # Cria Client explícito com a API key
        client = Client(api_key=LANGSMITH_API_KEY)
        # Instancia o tracer corretamente
        tracer = LangChainTracer(
            project_name="RAG-Project",
            client=client
        )
        callbacks.append(tracer)
        logger.info(
            "LangSmith tracing habilitado",
            extra={"handler": "LangChainTracer"}
        )
    else:
        logger.info("LangSmith tracing desabilitado")

    manager = CallbackManager(callbacks)
    logger.info(
        "CallbackManager inicializado",
        extra={"handlers": [type(cb).__name__ for cb in callbacks]}
    )
    return manager
