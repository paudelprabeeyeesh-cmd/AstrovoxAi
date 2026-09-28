"""Citation generation and source attribution for retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Citation:
    source_id: str
    title: str
    authors: list[str]
    year: int | None = None
    url: str | None = None
    snippet: str = ""


@dataclass
class CitedPassage:
    text: str
    citations: list[Citation]


class CitationGenerator:
    def __init__(self, format_style: str = "apa"):
        self.format_style = format_style

    def format_citation(self, citation: Citation) -> str:
        if self.format_style == "apa":
            author_str = ", ".join(citation.authors)
            year_str = f" ({citation.year})" if citation.year else ""
            result = f"{author_str}{year_str}. {citation.title}"
            if citation.url:
                result += f". Retrieved from {citation.url}"
            return result
        if self.format_style == "mla":
            author_str = ", ".join(citation.authors)
            year_str = f" ({citation.year})" if citation.year else ""
            return f'{author_str}{year_str}. "{citation.title}." {citation.url or ""}'
        return citation.title

    def generate_cited_response(self, passage_text: str, citations: list[Citation]) -> CitedPassage:
        formatted = []
        for i, citation in enumerate(citations, 1):
            formatted.append(f"[{i}] {self.format_citation(citation)}")
        citation_block = "\n".join(formatted)
        return CitedPassage(text=f"{passage_text}\n\n{citation_block}", citations=citations)

    def source_attribution(self, document_id: str, metadata: dict[str, Any]) -> Citation:
        return Citation(
            source_id=document_id,
            title=metadata.get("title", "Untitled"),
            authors=metadata.get("authors", ["Unknown"]),
            year=metadata.get("year"),
            url=metadata.get("url"),
            snippet=metadata.get("snippet", ""),
        )
