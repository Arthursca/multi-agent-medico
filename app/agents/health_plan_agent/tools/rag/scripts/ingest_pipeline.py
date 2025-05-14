# ingestion/ingest_pipeline.py

"""
ingestion.cli

CLI entrypoint to execute the full multimodal ingestion pipeline:
1. Load raw documents (including PDF detection)
2. Extract multimodal items from PDFs
3. Clean and normalize text
4. Chunk documents into controlled-size pieces
5. Generate embeddings for each chunk
6. Upsert embeddings into Postgres+pgvector VectorStore
"""

import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.agents.health_plan_agent.tools.rag.ingestion.loader import load_documents
from app.agents.health_plan_agent.tools.rag.ingestion.pdf_loader import load_pdf
from app.agents.health_plan_agent.tools.rag.ingestion.cleaner import clean_documents
from app.agents.health_plan_agent.tools.rag.ingestion.chunker import chunk_documents
from app.agents.health_plan_agent.tools.rag.embedding.embedder import generate_embedding
from app.agents.health_plan_agent.tools.rag.vectorstore.vector_store import VectorStore
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)


def run_ingestion(data_dir: Optional[str] = None) -> None:
    """
    Execute o pipeline completo de ingestão multimodal.

    Parameters
    ----------
    data_dir : Optional[str]
        Diretório base de onde carregar documentos. Se None, usa configuração em .env.
    """
    logger.info("Iniciando pipeline de ingestão multimodal", extra={"data_dir": data_dir})

    # 1. Carregar documentos brutos
    raw_docs: List[Dict[str, Any]] = load_documents(data_dir)
    logger.info("Documentos brutos carregados", extra={"count": len(raw_docs)})

    # 2. Extrair itens multimodais de PDFs
    multimodal_items: List[Dict[str, Any]] = []
    for doc in raw_docs:
        path = doc["metadata"].get("path", "")
        if Path(path).suffix.lower() == ".pdf":
            multimodal_items.extend(load_pdf(Path(path)))
        else:
            multimodal_items.append(doc)
    logger.info(
        "Itens multimodais preparados",
        extra={"total_items": len(multimodal_items)}
    )

    # 3. Limpeza e normalização
    cleaned_docs = clean_documents(multimodal_items)
    logger.info("Documentos limpos e normalizados", extra={"count": len(cleaned_docs)})

    # 4. Chunking de texto
    chunked_docs = chunk_documents(cleaned_docs)
    logger.info("Chunking concluído", extra={"total_chunks": len(chunked_docs)})

    # 5. Geração de embeddings
    docs_with_embeddings: List[Dict[str, Any]] = []
    for doc in chunked_docs:
        emb = generate_embedding(doc["content"])
        docs_with_embeddings.append({
            "content": doc["content"],
            "metadata": doc["metadata"],
            "embedding": emb
        })
    logger.info("Embeddings gerados", extra={"count": len(docs_with_embeddings)})

    # 6. Persistir no VectorStore
    vs = VectorStore()
    vs.add_documents(docs_with_embeddings)
    logger.info("Embeddings upsertados no VectorStore", extra={"count": len(docs_with_embeddings)})

    logger.info("Pipeline de ingestão multimodal finalizado com sucesso")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa pipeline multimodal de ingestão de documentos para RAG."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Diretório de dados (padrão: configurado em .env)"
    )
    args = parser.parse_args()
    run_ingestion(args.data_dir)
