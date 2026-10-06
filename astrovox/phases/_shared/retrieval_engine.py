"""Shared retrieval engine."""

from __future__ import annotations

from typing import Any

import numpy as np


class EmbeddingVector:
    """Small dense vector wrapper for phase embeddings."""

    def __init__(self, data: np.ndarray | list[float] | None = None, dim: int = 8):
        if isinstance(data, np.ndarray):
            self.data = np.asarray(data, dtype=np.float32).flatten()[:dim]
        else:
            self.data = np.zeros(dim, dtype=np.float32) if data is None else np.asarray(data, dtype=np.float32)[:dim]
        self.dim = self.data.shape[0]

    def normalize(self) -> "EmbeddingVector":
        n = np.linalg.norm(self.data)
        if n > 0:
            self.data = self.data / n
        return self

    def similarity(self, other: "EmbeddingVector") -> float:
        n1, n2 = np.linalg.norm(self.data), np.linalg.norm(other.data)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.dot(self.data, other.data) / (n1 * n2))

    def to_list(self) -> list[float]:
        return self.data.tolist()


def simple_text_embedding(text: str, dim: int = 8, normalize: bool = True) -> EmbeddingVector:
    """Deterministic text embedding from char n-gram counts (no ML dependency)."""
    counts = np.zeros(dim, dtype=np.float32)
    text = str(text).lower()
    for i in range(len(text) - 2):
        n = text[i:i + 3]
        idx = hash(n) % dim
        counts[idx] += 1.0
    if normalize:
        return EmbeddingVector(counts).normalize()
    return EmbeddingVector(counts)


class RetrievalEngine:
    """In-memory retrieval with text + embedding search."""

    def __init__(self):
        self.entries: list[dict] = []
        self.embeddings: dict[str, EmbeddingVector] = {}

    def add(self, key: str, value: Any, meta: dict | None = None) -> str:
        entry = {"key": key, "value": value, "meta": meta or {}}
        self.entries.append(entry)
        text = " ".join(str(v) for v in value.values()) if isinstance(value, dict) else str(value)
        self.embeddings[key] = simple_text_embedding(text)
        return key

    def search(self, query: str, limit: int = 50, use_embedding: bool = True) -> list[dict]:
        qvec = simple_text_embedding(query) if use_embedding else None
        scored: list[tuple[float, dict]] = []
        q = query.lower()
        for entry in self.entries:
            text = " ".join(str(v) for v in entry["value"].values()) if isinstance(entry["value"], dict) else str(entry["value"])
            kw = sum(text.lower().count(t) for t in q.split() if len(t) > 2)
            sim = qvec.similarity(self.embeddings[entry["key"]]) if use_embedding else 0.0
            scored.append((kw + sim * 10, entry))
        scored.sort(reverse=True)
        return [s[1] for s in scored[:limit]]

    def recall(self, key: str) -> dict | None:
        return next((e for e in self.entries if e["key"] == key), None)

    def count(self) -> int:
        return len(self.entries)

    def clear(self) -> None:
        self.entries.clear()
        self.embeddings.clear()
