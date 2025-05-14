from typing import List, Dict, Any
import json

from sqlalchemy import text
from app.agents.health_plan_agent.tools.rag.vectorstore.db import engine
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Manages storage and retrieval of vector embeddings in Postgres+pgvector.
    Provides methods to upsert embeddings and perform similarity search using HNSW indexing.
    """

    def __init__(self) -> None:
        """
        Initialize the VectorStore with a SQLAlchemy engine.
        Assumes that the Postgres extension pgvector and the 'docs' table
        with HNSW index are already created in vectorstore/db.py.
        """
        self.engine = engine

    def add_document(self, doc: Dict[str, Any]) -> None:
        """
        Insert or update a single document chunk embedding.

        Parameters
        ----------
        doc : Dict[str, Any]
            Document dict with keys:
              - 'content': str
              - 'metadata': dict (must include 'path'; may include 'chunk_index' and 'chunk_count')
              - 'embedding': List[float]
              - optionally 'id': str
        """
        metadata = doc.get("metadata", {})
        path = metadata.get("path")
        chunk_index = metadata.get("chunk_index")
        # Build a unique document ID per chunk when present
        if chunk_index is not None and path:
            doc_id = doc.get("id") or f"{path}_chunk_{chunk_index}"
        else:
            doc_id = doc.get("id") or path
        content = doc.get("content", "")
        embedding = doc.get("embedding", [])
        # Optionally, strip chunk-specific metadata if you don't want it stored
        metadata_to_store = metadata.copy()
        # metadata_to_store.pop("chunk_index", None)
        # metadata_to_store.pop("chunk_count", None)

        logger.info("Upserting document chunk into vector store", extra={"id": doc_id})
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO docs (id, content, metadata, embedding) "
                    "VALUES (:id, :content, :metadata, :embedding) "
                    "ON CONFLICT (id) DO UPDATE SET content = EXCLUDED.content, "
                    "metadata = EXCLUDED.metadata, embedding = EXCLUDED.embedding"
                ),
                {
                    "id": doc_id,
                    "content": content,
                    "metadata": json.dumps(metadata_to_store),
                    "embedding": embedding,
                },
            )
        logger.debug("Document chunk upserted", extra={"id": doc_id})

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """
        Batch insert or update multiple document chunks.

        Parameters
        ----------
        docs : List[Dict[str, Any]]
            List of document dictionaries (chunks).
        """
        logger.info("Batch upserting document chunks", extra={"count": len(docs)})
        with self.engine.begin() as conn:
            for doc in docs:
                self.add_document(doc)
        logger.debug("Batch upsert of chunks completed", extra={"count": len(docs)})

    def query_similar(self, vector: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """
        Query for the k most similar documents to the provided vector.

        Parameters
        ----------
        vector : List[float]
            Query embedding vector.
        k : int
            Number of similar documents to retrieve.

        Returns
        -------
        List[Dict[str, Any]]
            List of dicts with keys: 'id', 'content', 'metadata', 'distance'.
        """
        logger.info("Querying similar documents", extra={"k": k})
        with self.engine.connect() as conn:
            sql = """
            SELECT
              id,
              content,
              metadata,
              embedding <-> CAST(:vector AS vector) AS distance
            FROM docs
            ORDER BY embedding <-> CAST(:vector AS vector)
            LIMIT :k
            """
            result = conn.execute(
                text(sql),
                {"vector": vector, "k": k},
            )
            rows = result.mappings().all()
        logger.debug("Query returned rows", extra={"count": len(rows)})
        return [dict(row) for row in rows]

    def delete_document(self, doc_id: str) -> None:
        """
        Delete a document by its ID.

        Parameters
        ----------
        doc_id : str
            The ID of the document to delete.
        """
        logger.info("Deleting document", extra={"id": doc_id})
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM docs WHERE id = :id"), {"id": doc_id})
        logger.debug("Document deleted", extra={"id": doc_id})
