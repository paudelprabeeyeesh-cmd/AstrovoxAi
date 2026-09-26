"""Citation engine for RAG pipelines."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    style: str
    text: str
    authors: List[str] = field(default_factory=list)
    title: str = ""
    year: str = ""
    source: str = ""
    url: str = ""
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    confidence: float = 0.9


class CitationEngine:
    """Generate and manage citations for retrieved chunks."""

    STYLES = ("apa", "mla", "chicago", "ieee", "harvard", "vancouver")

    def generate(self, document_title: str, authors: List[str], year: str = "",
                 source: str = "", url: str = "", style: str = "apa",
                 page: Optional[int] = None, chunk_id: Optional[str] = None) -> Citation:
        year = year or str(datetime.now(timezone.utc).year)
        style = style.lower() if style in self.STYLES else "apa"
        text = getattr(self, f"_format_{style}")(authors, year, document_title, source, url, page)
        return Citation(style=style, text=text, authors=authors, title=document_title,
                        year=year, source=source, url=url, page=page, chunk_id=chunk_id)

    def generate_batch(self, references: List[Dict[str, Any]], style: str = "apa") -> List[Citation]:
        return [self.generate(
            document_title=r.get("title", ""),
            authors=r.get("authors", []),
            year=r.get("year", ""),
            source=r.get("source", ""),
            url=r.get("url", ""),
            style=style,
            page=r.get("page"),
            chunk_id=r.get("chunk_id"),
        ) for r in references]

    def extract_from_chunks(self, chunks: List[Any], style: str = "apa") -> List[Citation]:
        citations = []
        for chunk in chunks:
            meta = getattr(chunk, "metadata", {}) or {}
            if meta.get("source_type") and getattr(chunk, "content", ""):
                citations.append(self.generate(
                    document_title=meta.get("filename", "Unknown"),
                    authors=meta.get("authors", []),
                    year=meta.get("year", ""),
                    source=meta.get("source", ""),
                    url=meta.get("url", ""),
                    style=style,
                    chunk_id=getattr(chunk, "id", None),
                ))
        return citations

    def format_inline(self, citation: Citation, style: str = "apa") -> str:
        if style == "apa":
            parts = []
            if citation.authors:
                parts.append(", ".join(citation.authors[:2]) + (" et al." if len(citation.authors) > 2 else ""))
            parts.append(f"({citation.year})")
            return " ".join(parts)
        if style == "mla":
            return f"({citation.authors[0] if citation.authors else 'Unknown'} {citation.year})"
        return f"({citation.authors[0] if citation.authors else 'Unknown'}, {citation.year})"

    def to_bibliography(self, citations: List[Citation]) -> str:
        lines = []
        for i, c in enumerate(citations, 1):
            lines.append(f"[{i}] {c.text}")
        return "\n".join(lines)

    def _format_apa(self, authors, year, title, source, url, page):
        parts = [f"{', '.join(authors) if authors else 'Unknown'} ({year})." if year else f"{', '.join(authors) if authors else 'Unknown'}.",
                 f"{title}."]
        if source:
            parts.append(f"{source}.")
        if page:
            parts.append(f"p. {page}")
        if url:
            parts.append(url)
        return " ".join(parts)

    def _format_mla(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown Author"
        parts = [f'{author}. "{title}."']
        if source:
            parts.append(f"{source},")
        if page:
            parts.append(f"p. {page}.")
        if url:
            parts.append(url + ".")
        parts.append(f"{datetime.now(timezone.utc).strftime('%d %b. %Y')}.")
        return " ".join(parts)

    def _format_chicago(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f'{author}. "{title}."']
        if source:
            parts.append(f"{source}")
        if year:
            parts.append(f"({year}).")
        if page:
            parts.append(f"Page {page}.")
        if url:
            parts.append(url)
        return " ".join(parts)

    def _format_ieee(self, authors, title, year, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f'{author}, "{title},"']
        if source:
            parts.append(f"{source},")
        parts.append(f"{year}.")
        if page:
            parts.append(f"p. {page},")
        if url:
            parts.append(f"[Online]. Available: {url}.")
        return " ".join(parts)

    def _format_harvard(self, authors, year, title, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f"{author} ({year})"]
        parts.append(f"'{title}'")
        if source:
            parts.append(f", {source}")
        if page:
            parts.append(f", p. {page}")
        if url:
            parts.append(f". Available at: {url}")
        parts.append(".")
        return "".join(parts)

    def _format_vancouver(self, authors, title, year, source, url, page):
        author = ", ".join(authors) if authors else "Unknown"
        parts = [f"{author}. {title}."]
        if source:
            parts.append(f"{source};")
        parts.append(f"{year}.")
        if page:
            parts.append(f"p. {page}.")
        return " ".join(parts)
