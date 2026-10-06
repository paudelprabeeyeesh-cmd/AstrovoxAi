"""Semantic search using text embeddings."""

from __future__ import annotations

from astrovox.phases._shared.retrieval_engine import EmbeddingVector, simple_text_embedding


class SemanticSearch:
    """Semantic search over indexed documents."""

    def __init__(self, dim: int = 8):
        self.dim = dim
        self._docs: list[dict] = []
        self._vecs: list[EmbeddingVector] = []

    def add(self, key: str, text: str, metadata: dict | None = None) -> None:
        """Add a document."""
        text = str(text)
        self._docs.append({"key": key, "text": text, "metadata": metadata or {}})
        self._vecs.append(simple_text_embedding(text, dim=self.dim))

    def search(self, query: str, top: int = 10) -> list[dict]:
        """Search semantically."""
        qvec = simple_text_embedding(query, dim=self.dim)
        scored = [(qvec.similarity(v), doc) for v, doc in zip(self._vecs, self._docs)]
        scored.sort(reverse=True)
        return [{"key": d["key"], "score": s, "text": d["text"], "metadata": d["metadata"]}
                for s, d in scored[:top]]

    def count(self) -> int:
        return len(self._docs)

    def clear(self) -> None:
        self._docs.clear()
        self._vecs.clear()
