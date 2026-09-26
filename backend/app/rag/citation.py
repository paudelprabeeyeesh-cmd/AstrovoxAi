"""Citation generation and management for RAG pipelines."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    authors: List[str] = field(default_factory=list)
    year: str = ""
    source: str = ""
    url: str = ""
    style: str = "apa"
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def format(self) -> str:
        if self.style == "apa":
            return self._apa()
        if self.style == "mla":
            return self._mla()
        if self.style == "chicago":
            return self._chicago()
        if self.style == "bibtex":
            return self._bibtex()
        return self._plain()

    def _apa(self) -> str:
        authors = ", ".join(self.authors) if self.authors else "Unknown"
        year = f"({self.year})" if self.year else "(n.d.)"
        title = self.title or "Untitled"
        source = self.source or ""
        page = f"p. {self.page}" if self.page else ""
        parts = [f"{authors} {year}. {title}."]
        if source:
            parts.append(f" {source}.")
        if page:
            parts.append(f" {page}.")
        if self.url:
            parts.append(f" {self.url}")
        return "".join(parts)

    def _mla(self) -> str:
        authors = ", ".join(self.authors) if self.authors else "Unknown"
        title = self.title or "Untitled"
        source = self.source or ""
        page = f"p. {self.page}" if self.page else ""
        parts = [f'{authors}. "{title}."']
        if source:
            parts.append(f" {source},")
        if page:
            parts.append(f" {page}.")
        if self.url:
            parts.append(f" {self.url}.")
        return "".join(parts)

    def _chicago(self) -> str:
        authors = ", ".join(self.authors) if self.authors else "Unknown"
        title = self.title or "Untitled"
        source = self.source or ""
        parts = [f'{authors}. "{title}."']
        if source:
            parts.append(f" {source}.")
        if self.url:
            parts.append(f" Accessed via {self.url}.")
        return "".join(parts)

    def _bibtex(self) -> str:
        key = (self.authors[0].split()[-1] if self.authors else "unknown") + str(self.year or "nd")
        page = f"pages = {self.page}" if self.page else ""
        return (
            f"@misc{{{key},\n"
            f"  title = {{{self.title}}},\n"
            f"  author = {{{', '.join(self.authors)}}},\n"
            f"  year = {{{self.year}}},\n"
            f"  url = {{{self.url}}},\n"
            f"  howpublished = {{{self.source}}},\n"
            f"  {page}\n"
            f"}}"
        )

    def _plain(self) -> str:
        parts = [f"{self.title} - {self.source} ({self.year})"]
        if self.authors:
            parts[0] += f" by {', '.join(self.authors)}"
        if self.url:
            parts.append(self.url)
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "source": self.source,
            "url": self.url,
            "style": self.style,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "formatted": self.format(),
            "metadata": self.metadata,
        }


class CitationEngine:
    def __init__(self):
        self._citations: Dict[str, Citation] = {}

    def generate(
        self,
        document_title: str,
        authors: Optional[List[str]] = None,
        year: str = "",
        source: str = "",
        url: str = "",
        style: str = "apa",
        page: Optional[int] = None,
        chunk_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Citation:
        citation = Citation(
            title=document_title,
            authors=authors or [],
            year=year,
            source=source,
            url=url,
            style=style,
            page=page,
            chunk_id=chunk_id,
            metadata=metadata or {},
        )
        self._citations[citation.id] = citation
        return citation

    def get(self, citation_id: str) -> Optional[Citation]:
        return self._citations.get(citation_id)

    def list_citations(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._citations.values()]
