"""PDF document parser using a fallback extraction strategy."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class PDFPage:
    """A single page from a PDF document."""
    page_num: int
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"page_num": self.page_num, "text": self.text, "metadata": self.metadata}


@dataclass
class PDFDocument:
    """A parsed PDF document."""
    path: str
    pages: list[PDFPage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    page_count: int = 0

    def to_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    def to_dict(self) -> dict:
        return {"path": self.path, "page_count": self.page_count,
                "pages": [p.to_dict() for p in self.pages[:10]],
                "metadata": self.metadata}


class PDFParser:
    """Extract text from PDF files."""

    def __init__(self, use_external: bool = False):
        self.use_external = use_external
        self.last_error: str | None = None

    def parse(self, path: str | Path) -> PDFDocument:
        """Parse a PDF and extract text per page."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")
        try:
            return self._parse_with_lib(path)
        except Exception as e:
            self.last_error = str(e)
            return self._parse_fallback(path)

    def _parse_with_lib(self, path: Path) -> PDFDocument:
        import PyPDF2
        doc = PDFDocument(path=str(path))
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                doc.page_count = len(reader.pages)
                for i, page in enumerate(reader.pages):
                    doc.pages.append(PDFPage(page_num=i, text=page.extract_text() or ""))
            return doc
        except Exception:
            raise

    def _parse_fallback(self, path: Path) -> PDFDocument:
        """Fallback: extract raw text from the PDF bytes."""
        data = path.read_bytes()
        text_chunks = []
        for chunk in data.split(b"/Page"):
            chunk = chunk.split(b"endobj", 1)[0].split(b"BT", 1)[0]
            text = chunk.decode("latin-1", errors="ignore")
            lines = [l for l in text.split("\n") if l.strip() and len(l) > 5]
            text_chunks.append("\n".join(lines))
        doc = PDFDocument(path=str(path), page_count=max(1, len(text_chunks)))
        for i, t in enumerate(text_chunks):
            doc.pages.append(PDFPage(page_num=i, text=t.strip()))
        return doc

    def parse_many(self, paths: list[str]) -> list[PDFDocument]:
        """Parse multiple PDFs."""
        return [self.parse(p) for p in paths]

    def extract_text(self, path: str | Path) -> str:
        """Extract all text from a PDF."""
        return self.parse(path).to_text()
