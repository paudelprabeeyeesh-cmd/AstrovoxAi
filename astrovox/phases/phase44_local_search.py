"""In-memory keyword search over stored text."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchHit:
    """A single search hit."""
    key: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text,
                "metadata": self.metadata}


class LocalSearch:
    """Fast in-memory keyword search."""

    def __init__(self):
        self.index: dict[str, list[tuple[str, int]]] = {}
        self.documents: dict[str, dict] = {}

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Index a document."""
        text = str(text)
        self.documents[key] = {"text": text, "metadata": metadata or {}}
        tokens = text.lower().split()
        for token in tokens:
            self.index.setdefault(token, []).append((key, len(self.index.get(token, []))))

    def search(self, query: str, top: int = 10) -> list[SearchHit]:
        """Search for the query terms."""
        q = query.lower().split()
        scores: dict[str, float] = {}
        for token in q:
            for key, _ in self.index.get(token, []):
                scores[key] = scores.get(key, 0.0) + 1.0
        hits = []
        for key, score in scores.items():
            doc = self.documents[key]
            hits.append(SearchHit(key=key, score=score, text=doc["text"],
                                  metadata=doc.get("metadata", {})))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top]

    def count(self) -> int:
        return len(self.documents)

    def clear(self) -> None:
        self.index.clear()
        self.documents.clear()
