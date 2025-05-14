# pipeline/retriever.py

"""
pipeline.retriever

Implements the retrieval stage of the RAG pipeline: generates an embedding for
the query and retrieves the top-k most similar document chunks from the vectorstore.
"""

from typing import List, Dict, Any

from app.agents.health_plan_agent.tools.rag.embedding.embedder import generate_embedding
from app.agents.health_plan_agent.tools.rag.vectorstore.vector_store import VectorStore
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    """
    Retrieval component for the RAG pipeline.

    Provides a method to retrieve top-k relevant document chunks for a given query.
    """

    def __init__(self) -> None:
        self.vector_store = VectorStore()

    def retrieve(self, query: str, k: int = 2) -> List[Dict[str, Any]]:
        """
        Generate an embedding for the query and retrieve the top-k similar documents.

        Parameters
        ----------
        query : str
            The input text query.
        k : int, optional
            Number of similar documents to retrieve (default is 2).

        Returns
        -------
        List[Dict[str, Any]]
            A list of dicts, each containing keys: 'id', 'content', 'metadata', 'distance'.
        """
        logger.info("Starting retrieval", extra={"query_length": len(query), "k": k})
        try:
            vector = generate_embedding(query)
        except Exception as e:
            logger.error("Failed to generate embedding for retrieval", extra={"error": str(e)})
            raise

        if not vector:
            logger.warning("Empty embedding vector returned; no retrieval performed")
            return []

        results = self.vector_store.query_similar(vector, k)
        logger.info("Retrieval completed", extra={"results_count": len(results)})
        return results
