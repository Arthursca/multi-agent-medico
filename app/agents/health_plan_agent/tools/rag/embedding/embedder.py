"""
embedder.py

This module is responsible for generating text embeddings using the LangChain
wrapper for OpenAI embeddings (text-embedding-3-small model).
"""

# =======================
# Imports and Dependencies
# =======================

from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_openai import OpenAIEmbeddings

from app.config import OPENAI_API_KEY, LLM_PROVIDER
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

# =======================
# Logger Initialization
# =======================

logger = get_logger(__name__)

# =======================
# Embedding Client Setup
# =======================

if LLM_PROVIDER.lower() == "openai":
    embeddings_client = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY,
    )
else:
    embeddings_client = None

# =======================
# Internal Helper Function
# =======================

@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    stop=stop_after_attempt(3),
)
def _request_embedding(text: str) -> List[float]:
    """
    Internal helper that invokes LangChain's embed_query method with retry logic.

    Parameters
    ----------
    text : str
        Input text to be embedded.

    Returns
    -------
    List[float]
        Embedding vector as a list of floats.
    """
    return embeddings_client.embed_query(text)

# =======================
# Public API
# =======================

def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given input text.

    Parameters
    ----------
    text : str
        Text input to generate the embedding for.

    Returns
    -------
    List[float]
        A float list representing the text embedding.

    Raises
    ------
    NotImplementedError
        If the configured provider does not support embeddings.
    Exception
        If the embedding request fails.
    """
    if not text:
        logger.warning(
            "Texto vazio recebido para embedding; retornando vetor vazio"
        )
        return []

    logger.info(
        "Gerando embedding",
        extra={"provider": LLM_PROVIDER, "text_length": len(text)},
    )

    if LLM_PROVIDER.lower() != "openai" or embeddings_client is None:
        error_msg = f"Embedding provider '{LLM_PROVIDER}' não implementado"
        logger.error(error_msg)
        raise NotImplementedError(error_msg)

    try:
        vector = _request_embedding(text)
        logger.debug(
            "Embedding gerado com sucesso",
            extra={"vector_length": len(vector)},
        )
        return vector
    except Exception as e:
        logger.error(
            "Falha ao gerar embedding",
            extra={"error": str(e)},
        )
        raise
