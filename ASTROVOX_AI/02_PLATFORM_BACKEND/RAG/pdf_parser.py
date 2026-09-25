"""RAG: PDF parser."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class PDFParser:
    def parse(self, file_path: str) -> List[str]:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"PDF not found: {file_path}")
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
        logger.info(f"Parsed {len(chunks)} chunks from {file_path}")
        return chunks


_pdf_parser = PDFParser()


def get_pdf_parser() -> PDFParser:
    return _pdf_parser
