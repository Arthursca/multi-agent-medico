"""
cleaner.py

Loads and sanitizes documents from various formats, converting them to Markdown format.

"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from PyPDF2 import PdfReader
import mammoth
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

# Logger Initialization
logger = get_logger(__name__)

# Exception Class
class DocumentCleanerError(Exception):
    """Raised when a document cannot be cleaned or converted to Markdown."""

# Text Extraction Functions
def load_pdf_text(path: Path) -> str:
    """
    Extracts text from a PDF file.

    Parameters
    ----------
    path : Path
        Path to the PDF file.

    Returns
    -------
    str
        Extracted text from all pages.
    """
    reader = PdfReader(str(path))
    pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n\n".join(pages_text)

def load_other_text(path: Path) -> Optional[str]:
    """
    Loads and converts supported non-PDF files to Markdown.

    Parameters
    ----------
    path : Path
        Path to the file.

    Returns
    -------
    Optional[str]
        Markdown-formatted string or None if format unsupported.
    """
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return path.read_text(encoding="utf-8")
    elif suffix == ".docx":
        with path.open("rb") as docx_file:
            result = mammoth.convert_to_markdown(docx_file)
            return result.value
    else:
        logger.warning("Formato não suportado para conversão direta",
                       extra={"file": str(path), "suffix": suffix})
        return None

# Document Cleaning Function
def clean_documents(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Cleans, normalizes, deduplicates, and converts documents to Markdown.

    Parameters
    ----------
    documents : List[Dict[str, Any]]
        List of dictionaries with 'metadata' including 'file_path'.

    Returns
    -------
    List[Dict[str, Any]]
        Cleaned and Markdown-formatted documents.
    """
    logger.info("Iniciando limpeza e conversão de documentos",
                extra={"total_documents": len(documents)})

    cleaned_docs: List[Dict[str, Any]] = []
    seen_contents: set[str] = set()

    for doc in documents:
        metadata = doc.get("metadata", {}).copy()
        file_path = metadata.get("file_path") or metadata.get("path")
        if not file_path:
            logger.warning("Ignorando documento sem file_path",
                           extra={"metadata": metadata})
            continue

        path_obj = Path(file_path)
        if not path_obj.is_file():
            logger.warning("Ignorando arquivo inexistente ou inválido",
                           extra={"file": file_path})
            continue

        try:
            suffix = path_obj.suffix.lower()
            if suffix == ".pdf":
                markdown_text = load_pdf_text(path_obj)
            else:
                markdown_text = load_other_text(path_obj)
                if markdown_text is None:
                    raise DocumentCleanerError(f"Formato não suportado: {suffix}")
        except Exception as exc:
            logger.warning("Erro ao processar documento, ignorando",
                           extra={"file": file_path, "error": str(exc)})
            continue

        if markdown_text in seen_contents:
            logger.debug("Conteúdo duplicado, ignorando", extra={"file": file_path})
            continue

        seen_contents.add(markdown_text)
        cleaned_docs.append({"content": markdown_text, "metadata": metadata})
        logger.debug("Documento limpo e convertido para Markdown",
                     extra={"file": file_path, "length": len(markdown_text)})

    logger.info("Limpeza e conversão concluídas",
                extra={"cleaned_documents": len(cleaned_docs)})
    return cleaned_docs