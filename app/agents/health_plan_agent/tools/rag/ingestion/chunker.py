"""
chunker.py

Splits cleaned documents into manageable chunks while retaining and annotating metadata.
"""

from typing import Any, Dict, List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

# Logger Initialization
logger = get_logger(__name__)

# Chunking Functionality
def chunk_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Splits cleaned text documents into fixed-size chunks while preserving and annotating metadata.

    Parameters
    ----------
    documents : List[Dict[str, Any]]
        A list of dictionaries with 'content' (str) and 'metadata' (dict).

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries each containing:
        - 'content': str, chunked text
        - 'metadata': dict, extended with:
            * 'chunk_index': index of the chunk
            * 'chunk_count': total number of chunks
    """
    logger.info("Iniciando chunking de documentos", extra={"total_documents": len(documents)})

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )

    chunked_docs: List[Dict[str, Any]] = []
    total_chunks = 0

    for doc in documents:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {})
        chunks = text_splitter.split_text(content)
        chunk_count = len(chunks)

        for idx, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = idx
            chunk_metadata["chunk_count"] = chunk_count
            chunked_docs.append({"content": chunk, "metadata": chunk_metadata})

        total_chunks += chunk_count
        logger.debug("Documento fragmentado", extra={
            "file": metadata.get("file_name"),
            "chunks_generated": chunk_count
        })

    logger.info("Chunking concluído", extra={"total_chunks": total_chunks})
    return chunked_docs