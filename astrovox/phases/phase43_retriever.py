"""Vector similarity retrieval over embedded chunks."""

from __future__ import annotations

from typing import Any

from astrovox.phases._shared.base import BaseStore
from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding
from astrovox.phases._shared.ranking import Ranker


class VectorRetriever:
    """Retrieve chunks by vector similarity."""

    def __init__(self, store: BaseStore, dim: int = 8, top_k: int = 10,
                 min_score: float = 0.0):
        self.store = store
        self.dim = dim
        self.top_k = top_k
        self.min_score = min_score
        self.ranker = Ranker()

    def search(self, query: str, filters: dict | None = None, top: int | None = None) -> list[dict]:
        """Retrieve most similar chunks for a query."""
        top = top or self.top_k
        qvec = simple_text_embedding(query, dim=self.dim)
        results = []
        for key in self.store.list_keys():
            if filters and not self._matches(key, filters):
                continue
            entry = self.store.get(key)
            if not isinstance(entry, dict):
                continue
            emb_key = f"{key}:embedding"
            emb_data = self.store.get(emb_key)
            if isinstance(emb_data, dict) and "embedding" in emb_data:
                emb = EmbeddingVector(emb_data["embedding"], dim=self.dim)
            else:
                emb = qvec
            score = qvec.similarity(emb)
            if score >= self.min_score:
                results.append({"key": key, "score": score, "text": entry.get("text", ""),
                                "metadata": entry.get("metadata", {})})
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top]

    def _matches(self, key: str, filters: dict) -> bool:
        for k, v in filters.items():
            if k not in key:
                return False
        return True

    def top_similar(self, text: str, top: int | None = None) -> list[dict]:
        """Find the most similar stored items to a text."""
        qvec = simple_text_embedding(text, dim=self.dim)
        scored = []
        for key in self.store.list_keys():
            if not key.endswith(":embedding"):
                continue
            emb_data = self.store.get(key)
            if isinstance(emb_data, dict):
                emb = EmbeddingVector(emb_data["embedding"], dim=self.dim)
                scored.append((qvec.similarity(emb), key))
        scored.sort(reverse=True)
        out = []
        for score, key in scored[:top or self.top_k]:
            k = key.replace(":embedding", "")
            entry = self.store.get(k)
            out.append({"key": k, "score": score,
                        "text": entry.get("text", "") if isinstance(entry, dict) else str(entry)})
        return out
