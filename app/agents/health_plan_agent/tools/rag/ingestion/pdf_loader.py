# ingestion/pdf_loader.py

"""
ingestion.pdf_loader

Extrai conteúdos multimodais (texto, tabelas e imagens) de PDFs complexos,
devolvendo uma lista de “document items” compatíveis com o pipeline de RAG.

Cada item é um dict com:
- 'content': str (para texto ou representação textual de tabela) ou base64 de imagem
- 'type': 'text' | 'table' | 'image'
- 'metadata': dict com chaves:
    * file_name, path, page_number
    * para tabelas: table_index
    * para imagens: image_index, xref
"""

from pathlib import Path
from typing import Any, Dict, List

import base64

import fitz  # PyMuPDF para texto e imagens
import pandas as pd
import tabula  # para extração de tabelas em DataFrame

from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)


DocumentItem = Dict[str, Any]


def _encode_image(pix: fitz) -> str:
    """
    Recebe um Pixmap do PyMuPDF e retorna uma string base64 do PNG.
    """
    buf = pix.tobytes(output="png")
    return base64.b64encode(buf).decode("utf-8")


def load_pdf(path: Path) -> List[DocumentItem]:
    """
    Para cada página do PDF em *path*, extrai:
      1. Texto bruto (via page.get_text())
      2. Cada tabela (via tabula.read_pdf → DataFrame → Markdown-like)
      3. Cada imagem inline (via page.get_images)
    Retorna lista de dicts DocumentItem.
    """
    logger.info("Carregando PDF multimodal", extra={"file": str(path)})
    docs: List[DocumentItem] = []
    doc = fitz.open(str(path))
    for pno in range(len(doc)):
        page = doc[pno]
        meta_base = {
            "file_name": path.name,
            "path": str(path.resolve()),
            "page_number": pno + 1,
        }

        # 1. Texto
        text = page.get_text().strip()
        if text:
            docs.append({
                "type": "text",
                "content": text,
                "metadata": meta_base.copy()
            })

        # 2. Tabelas
        try:
            # Extrai todas as tabelas da página
            df_list: List[pd.DataFrame] = tabula.read_pdf(
                str(path),
                pages=pno + 1,
                multiple_tables=True,
                pandas_options={"dtype": str},
            )
            for idx, df in enumerate(df_list):
                # Converte DataFrame em texto tabular simples
                table_txt = df.to_csv(sep=" | ", index=False).strip()
                md = meta_base.copy()
                md["type"] = "table"
                md["table_index"] = idx
                docs.append({
                    "type": "table",
                    "content": table_txt,
                    "metadata": md
                })
        except Exception as e:
            logger.warning(
                "Falha ao extrair tabela",
                extra={"file": str(path), "page": pno + 1, "error": str(e)}
            )

        # 3. Imagens
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = fitz.Pixmap(doc, xref)
                b64 = _encode_image(pix)
                md = meta_base.copy()
                md["type"] = "image"
                md["image_index"] = img_index
                md["xref"] = xref
                docs.append({
                    "type": "image",
                    "content": b64,
                    "metadata": md
                })
                pix = None  # libera memória
            except Exception as e:
                logger.warning(
                    "Falha ao extrair imagem",
                    extra={"file": str(path), "page": pno + 1, "xref": xref, "error": str(e)}
                )

    logger.info(
        "Extração multimodal concluída",
        extra={"file": str(path), "items_extracted": len(docs)}
    )
    return docs
