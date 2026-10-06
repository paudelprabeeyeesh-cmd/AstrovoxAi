"""Re-rank retrieved results using scoring heuristics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RankedResult:
    """A ranked retrieval result."""
    item: dict
    relevance_score: float
    position: int

    def to_dict(self) -> dict:
        return {"item": self.item, "relevance_score": self.relevance_score,
                "position": self.position}


class SimpleReranker:
    """Re-rank results using hybrid scoring (no external model needed)."""

    def __init__(self, use_keyword: bool = True, use_overlap: bool = True,
                 use_position: bool = True):
        self.use_keyword = use_keyword
        self.use_overlap = use_overlap
        self.use_position = use_position

    def _keyword_overlap(self, query: str, text: str) -> float:
        q = query.lower().split()
        t = text.lower().split()
        if not q or not t:
            return 0.0
        common = set(q) & set(t)
        return len(common) / len(q)

    def _embed_overlap(self, query: str, text: str, dim: int = 8) -> float:
        from astrovox.phases._shared.retrieval_engine import simple_text_embedding
        q = simple_text_embedding(query, dim=dim)
        t = simple_text_embedding(text, dim=dim)
        return q.similarity(t)

    def score_item(self, query: str, item: dict) -> float:
        """Score a single item against the query."""
        text = item.get("text", "")
        score = 0.0
        if self.use_keyword:
            score += 3.0 * self._keyword_overlap(query, text)
        if self.use_overlap:
            score += 2.0 * self._embed_overlap(query, text)
        if self.use_position and "position" in item:
            score += 1.0 / (1.0 + item["position"])
        return score

    def rerank(self, query: str, items: list[dict], top: int = 10) -> list[RankedResult]:
        """Re-rank a list of items by relevance to the query."""
        scored = []
        for i, item in enumerate(items):
            s = self.score_item(query, item)
            scored.append(RankedResult(item=item, relevance_score=s, position=i))
        scored.sort(key=lambda r: r.relevance_score, reverse=True)
        return scored[:top]

    def rerank_store(self, store, query: str, top: int = 10) -> list[RankedResult]:
        """Retrieve and rerank from a store."""
        keys = list(store.list_keys())[:50]
        items = []
        for i, k in enumerate(keys):
            entry = store.get(k)
            if isinstance(entry, dict):
                items.append({"key": k, "text": entry.get("text", ""), "position": i})
        return self.rerank(query, items, top=top)
