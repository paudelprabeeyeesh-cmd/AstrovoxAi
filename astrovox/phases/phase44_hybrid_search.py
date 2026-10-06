"""Fuse keyword and vector search results."""

from __future__ import annotations

from typing import Any

from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding
from astrovox.phases._shared.ranking import hybrid_rank


class HybridSearch:
    """Fuse keyword and semantic search results."""

    def __init__(self, keyword_weight: float = 0.5, semantic_weight: float = 0.5,
                 dim: int = 8):
        self.keyword_weight = keyword_weight
        self.semantic_weight = semantic_weight
        self.dim = dim
        self._keywords: dict[str, dict] = {}
        self._embeddings: dict[str, EmbeddingVector] = {}
        self._docs: dict[str, dict] = {}

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Add a document to the hybrid index."""
        text = str(text)
        self._keywords.setdefault(key, {"count": 0})
        for token in text.lower().split():
            self._keywords.setdefault(token, []).append(key)
            self._keywords[key]["count"] = self._keywords[key].get("count", 0) + 1
        self._embeddings[key] = simple_text_embedding(text, dim=self.dim)
        self._docs[key] = {"text": text, "metadata": metadata or {}}

    def search(self, query: str, top: int = 10) -> list[dict]:
        """Fuse keyword and semantic results."""
        q = query.lower()
        # Keyword scores.
        kw_scores: dict[str, float] = {}
        for token in q.split():
            for key in self._keywords.get(token, []):
                kw_scores[key] = kw_scores.get(key, 0.0) + 1.0
        # Semantic score.
        qvec = simple_text_embedding(query, dim=self.dim)
        sem_scores: dict[str, float] = {}
        for key, vec in self._embeddings.items():
            sem_scores[key] = qvec.similarity(vec)
        # Fuse.
        all_keys = set(kw_scores) | set(sem_scores)
        scored = []
        for key in all_keys:
            kw = kw_scores.get(key, 0.0) / max(self._keywords.get(key, {}).get("count", 1), 1)
            sem = sem_scores.get(key, 0.0)
            total = kw * self.keyword_weight + sem * self.semantic_weight
            scored.append((total, key))
        scored.sort(reverse=True)
        out = []
        for score, key in scored[:top]:
            doc = self._docs[key]
            out.append({"key": key, "score": score, "text": doc["text"],
                        "metadata": doc.get("metadata", {})})
        return out

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._keywords.clear()
        self._embeddings.clear()
        self._docs.clear()
