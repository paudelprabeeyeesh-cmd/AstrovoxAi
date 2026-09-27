"""Document parser for PDF, DOCX, TXT, and image files."""
from __future__ import annotations

import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class DocumentParser:
    def __init__(self) -> None:
        self._supported_types = {
            "application/pdf": self._parse_pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._parse_docx,
            "text/plain": self._parse_text,
            "text/markdown": self._parse_text,
            "image/png": self._parse_image,
            "image/jpeg": self._parse_image,
        }

    def parse(self, content: bytes, content_type: str, filename: str) -> dict:
        parser = self._supported_types.get(content_type)
        if not parser:
            raise ValueError(f"Unsupported content type: {content_type}")
        return parser(content, filename)

    def _parse_pdf(self, content: bytes, filename: str) -> dict:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return {"text": text, "chunks": self._chunk(text), "metadata": {"pages": len(reader.pages), "source": filename}}
        except ImportError:
            raise RuntimeError("pypdf is not installed")

    def _parse_docx(self, content: bytes, filename: str) -> dict:
        try:
            from docx import Document as DocxDocument
            doc = DocxDocument(io.BytesIO(content))
            text = "\n".join(paragraph.text for paragraph in doc.paragraphs)
            return {"text": text, "chunks": self._chunk(text), "metadata": {"source": filename}}
        except ImportError:
            raise RuntimeError("python-docx is not installed")

    def _parse_text(self, content: bytes, filename: str) -> dict:
        text = content.decode("utf-8", errors="replace")
        return {"text": text, "chunks": self._chunk(text), "metadata": {"source": filename}}

    def _parse_image(self, content: bytes, filename: str) -> dict:
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
            return {"text": text, "chunks": self._chunk(text), "metadata": {"source": filename, "image_size": image.size}}
        except ImportError:
            raise RuntimeError("pytesseract or PIL is not installed")

    def _chunk(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if not text or not text.strip():
            return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            remaining = len(text) - start
            if remaining < overlap and chunks:
                break
            chunk = text[start:min(end, len(text))]
            if chunk.strip():
                chunks.append(chunk.strip())
            start = end - overlap
            if start >= len(text):
                break
        return chunks
