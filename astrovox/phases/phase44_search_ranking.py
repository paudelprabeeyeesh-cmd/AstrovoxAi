"""Search result ranking with recency and metadata boosts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankedHit:
    """A ranked search hit."""
    key: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "text": self.text,
                "metadata": self.metadata}


class SearchRanker:
    """Apply boosting factors to search results."""

    def __init__(self, recency_weight: float = 0.3, meta_boost: dict | None = None,
                 min_score: float = 0.0):
        self.recency_weight = recency_weight
        self.meta_boost = meta_boost or {}
        self.min_score = min_score

    def score(self, hit: dict, query: str | None = None) -> float:
        """Compute final score for a hit."""
        score = hit.get("score", 0.0)
        meta = hit.get("metadata", {})
        # Recency boost.
        created = meta.get("created", time.time())
        recency = 1.0 / (1.0 + (time.time() - created))
        score += self.recency_weight * recency * 10.0
        # Metadata boosts.
        for field_name, boost_val in self.meta_boost.items():
            if field_name in meta and meta[field_name] == boost_val:
                score += 1.0
        return score

    def rank(self, hits: list[dict], query: str | None = None, top: int = 10) -> list[RankedHit]:
        """Rank hits with boosting applied."""
        scored = []
        for h in hits:
            s = self.score(h, query)
            if s >= self.min_score:
                scored.append(RankedHit(key=h.get("key", ""), score=s, text=h.get("text", ""),
                                        metadata=h.get("metadata", {})))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top]

    def boost_field(self, field_name: str, value: Any, boost: float = 1.0) -> None:
        """Add a metadata boost rule."""
        self.meta_boost[field_name] = value
        self.meta_boost[f"{field_name}:boost"] = boost
