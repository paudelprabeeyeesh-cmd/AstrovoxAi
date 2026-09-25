"""
PDF parsing and document chunking for RAG.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    text: str
    metadata: dict
    chunk_id: str
    page_number: Optional[int] = None
    start_char: int = 0
    end_char: int = 0


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64, metadata: Optional[dict] = None) -> List[DocumentChunk]:
    """Split text into overlapping chunks."""
    chunks = []
    metadata = metadata or {}
    start = 0
    chunk_id = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]
        chunks.append(DocumentChunk(text=chunk_text, metadata=metadata, chunk_id=f"chunk_{chunk_id}", start_char=start, end_char=end))
        chunk_id += 1
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except ImportError:
        logger.warning("PyMuPDF not available, trying pdfminer")
        try:
            from pdfminer.high_level import extract_text
            return extract_text(file_path)
        except ImportError:
            logger.error("No PDF library available")
            return ""
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def parse_pdf_to_chunks(file_path: str, chunk_size: int = 512, overlap: int = 64) -> List[DocumentChunk]:
    """Parse PDF and return chunked documents."""
    text = extract_text_from_pdf(file_path)
    if not text:
        return []
    metadata = {"source": file_path, "type": "pdf"}
    return chunk_text(text, chunk_size=chunk_size, metadata=metadata)
