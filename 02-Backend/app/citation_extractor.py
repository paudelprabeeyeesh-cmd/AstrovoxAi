"""Citation extractor for grounding and source attribution."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    source_type: str
    source_id: str
    content: str
    confidence: float
    span_start: int = 0
    span_end: int = 0
    metadata: dict = field(default_factory=dict)


class CitationExtractor:
    SOURCE_PATTERNS = {
        "memory": re.compile(r"\[memory:(?P<id>[^\]]+)\]", re.I),
        "knowledge": re.compile(r"\[knowledge:(?P<id>[^\]]+)\]", re.I),
        "document": re.compile(r"\[doc:(?P<id>[^\]]+)\]", re.I),
        "url": re.compile(r"https?://[^\s)]+", re.I),
        "reference": re.compile(r"\[ref:(?P<id>[^\]]+)\]", re.I),
    }

    def extract(self, text: str, sources: Optional[list[dict[str, Any]]] = None) -> list[Citation]:
        citations: list[Citation] = []
        for source_type, pattern in self.SOURCE_PATTERNS.items():
            for match in pattern.finditer(text):
                span_start = match.start()
                span_end = match.end()
                if source_type in ("url",):
                    citation = Citation(
                        source_type="url",
                        source_id=match.group(0),
                        content=match.group(0),
                        confidence=0.8,
                        span_start=span_start,
                        span_end=span_end,
                    )
                else:
                    source_id = match.group("id")
                    citation = Citation(
                        source_type=source_type,
                        source_id=source_id,
                        content=match.group(0),
                        confidence=0.9,
                        span_start=span_start,
                        span_end=span_end,
                    )
                if sources:
                    matched = next((s for s in sources if s.get("id") == citation.source_id), None)
                    if matched:
                        citation.confidence = matched.get("confidence", citation.confidence)
                        citation.metadata = matched.get("metadata", {})
                citations.append(citation)
        citations.sort(key=lambda c: c.span_start)
        return citations

    def format_citations(self, citations: list[Citation], style: str = "inline") -> str:
        if not citations:
            return ""
        if style == "inline":
            parts = []
            for i, c in enumerate(citations, 1):
                parts.append(f"[{i}] {c.source_type}:{c.source_id} (confidence={c.confidence:.2f})")
            return "\n".join(parts)
        if style == "numbered":
            seen = {}
            for c in citations:
                key = c.source_id
                if key not in seen:
                    seen[key] = len(seen) + 1
            return " ".join(f"[{seen[c.source_id]}]" for c in citations)
        return ""

    def attach_metadata(self, text: str, citations: list[Citation]) -> str:
        annotated = text
        for i, c in enumerate(reversed(citations), 1):
            marker = f" [{i}]"
            if c.span_end <= len(annotated):
                annotated = annotated[:c.span_end] + marker + annotated[c.span_end:]
        return annotated
