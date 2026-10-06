"""Generate citations for retrieved sources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Citation:
    """A citation linking generated text to a source."""
    ref_id: str
    source_key: str
    source_label: str
    snippet: str
    position: int = 0

    def to_dict(self) -> dict:
        return {"ref_id": self.ref_id, "source_key": self.source_key,
                "source_label": self.source_label, "snippet": self.snippet,
                "position": self.position}

    def format(self) -> str:
        return f"[{self.ref_id}] {self.source_label}: {self.snippet[:80]}"


class CitationEngine:
    """Generate citations for retrieved sources."""

    def __init__(self, start: int = 1):
        self.start = start
        self.refs: list[Citation] = []

    def cite(self, source_key: str, source_label: str, snippet: str,
             position: int = 0) -> Citation:
        """Create a citation for a source."""
        ref_id = f"[{self.start + len(self.refs)}]"
        cit = Citation(ref_id=ref_id, source_key=source_key, source_label=source_label,
                       snippet=snippet, position=position)
        self.refs.append(cit)
        return cit

    def cite_batch(self, sources: list[dict]) -> list[Citation]:
        """Create citations for multiple sources."""
        return [self.cite(s.get("key", ""), s.get("label", "source"),
                          s.get("snippet", s.get("text", "") or "")[:200]) for s in sources]

    def build_response(self, response: str) -> str:
        """Append citations to a response."""
        out = response
        if self.refs:
            out += "\n\n---\nSources:\n"
            out += "\n".join(c.format() for c in self.refs)
        return out

    def clear(self) -> None:
        self.refs.clear()

    def list_citations(self) -> list[dict]:
        return [c.to_dict() for c in self.refs]
