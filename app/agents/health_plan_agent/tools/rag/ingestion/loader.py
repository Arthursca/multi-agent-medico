"""ingestion.loader

Initial document-loading stage for the RAG pipeline.

This module walks through the ``data/`` directory (or a custom directory passed
at runtime) and loads **all** files it finds, returning a list of dictionaries
with the raw content and basic metadata.  No cleaning or chunking is performed
here – that is handled by ``ingestion.cleaner`` and subsequent steps.

Key features
------------
* Recursively discovers files in the target directory.
* Reads each file in binary mode, then decodes to UTF-8 (gracefully handling
  decoding errors).
* Collects essential metadata: absolute path, file name, size (bytes) and last
  modification timestamp.
...
* Raises ``DocumentLoaderError`` for unreadable or empty files (continues
  processing other files).

Environment
-----------
The base data directory defaults to ``settings.DATA_DIR`` (from
``utils.config``).  Override by passing ``data_dir`` explicitly or setting the
``DATA_DIR`` variable in your ``.env``.

Examples
--------
>>> from app.agents.health_plan_agent.tools.rag import load_documents
>>> docs = load_documents()                 # uses settings.DATA_DIR
>>> docs = load_documents(Path("/tmp/in/")) # custom directory

"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger: logging.Logger = get_logger(__name__)


class DocumentLoaderError(Exception):
    """Raised when a document cannot be loaded or is invalid."""


def _read_file(path: Path) -> str:
    """Read *path* and return UTF-8 text, replacing undecodable bytes."""
    try:
        with path.open("rb") as fh:
            raw: bytes = fh.read()
            if len(raw) == 0:
                raise DocumentLoaderError(f"{path} is empty")
            return raw.decode("utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as exc:  # pragma: no cover
        raise DocumentLoaderError(f"Failed reading {path}: {exc}") from exc


def _collect_metadata(path: Path, size: int) -> Dict[str, Any]:
    """Return a metadata dictionary for *path*."""
    stat = path.stat()
    return {
        "file_name": path.name,
        "path": str(path.resolve()),
        "size_bytes": size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


def load_documents(data_dir: Path | str | None = None) -> List[Dict[str, Any]]:
    """Load every file under *data_dir* and return a list of document objects.

    Parameters
    ----------
    data_dir
        Base directory to search.  If *None*, ``settings.DATA_DIR`` is used.

    Returns
    -------
    List[Dict[str, Any]]
        Each dict has keys: ``content`` (str) and ``metadata`` (dict).

    Raises
    ------
    FileNotFoundError
        If the provided directory does not exist or is not a directory.
    """
    base_dir = Path(data_dir or settings.DATA_DIR).expanduser().resolve()

    if not base_dir.is_dir():
        raise FileNotFoundError(f"{base_dir} is not a directory")

    logger.info("Starting document load", extra={"data_dir": str(base_dir)})

    documents: List[Dict[str, Any]] = []

    for path in base_dir.rglob("*"):
        if not path.is_file():
            continue  # skip sub-directories

        try:
            content: str = _read_file(path)
        except DocumentLoaderError as err:
            logger.warning(
                "Skipping unreadable file",
                extra={"path": str(path), "error": str(err)},
            )
            continue

        meta: Dict[str, Any] = _collect_metadata(path, size=len(content.encode("utf-8")))
        documents.append({"content": content, "metadata": meta})

        logger.debug(
            "Loaded file",
            extra={
                "path": meta["path"],
                "size_bytes": meta["size_bytes"],
                "modified_at": meta["modified_at"],
            },
        )

    logger.info("Completed document load", extra={"total_files": len(documents)})
    return documents
