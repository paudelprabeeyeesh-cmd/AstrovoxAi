"""Similarity search over stored vectors."""

from __future__ import annotations

import math
from typing import Any


class SimSearch:
    """Similarity search using cosine distance."""

    def __init__(self, vectors: dict[str, list[float]] | None = None):
        self.vectors = vectors or {}

    def _cosine(self, a: list[float], b: list[float]) -> float:
        n1 = math.sqrt(sum(x * x for x in a))
        n2 = math.sqrt(sum(x * x for x in b))
        if n1 == 0 or n2 == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (n1 * n2)

    def search(self, query: list[float], top: int = 10,
               threshold: float = 0.0) -> list[tuple[str, float]]:
        """Brute-force similarity search."""
        scored = [(self._cosine(query, v), vid) for vid, v in self.vectors.items()]
        scored.sort(reverse=True)
        return [(vid, s) for vid, s in scored if s >= threshold][:top]

    def add(self, vid: str, vector: list[float]) -> None:
        self.vectors[vid] = vector

    def remove(self, vid: str) -> bool:
        if vid in self.vectors:
            del self.vectors[vid]
            return True
        return False

    def count(self) -> int:
        return len(self.vectors)

    def reset(self) -> None:
        self.vectors.clear()


class NaiveHNSW:
    """Naive HNSW-like index for faster ANN search."""

    def __init__(self, vectors: dict[str, list[float]] | None = None, m: int = 4, ef_construction: int = 20):
        self.m = m
        self.ef_construction = ef_construction
        self.vectors = vectors or {}
        self.index: dict[str, list[str]] = {}
        self._build()

    def _build(self) -> None:
        for vid, vec in self.vectors.items():
            self.index[vid] = self._connect(vec)

    def _connect(self, vec: list[float]) -> list[str]:
        scores = [(self._cosine(vec, v), vid) for vid, v in self.vectors.items()]
        scores.sort(reverse=True)
        return [vid for vid, _ in scores[:self.m]]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        n1 = math.sqrt(sum(x * x for x in a))
        n2 = math.sqrt(sum(x * x for x in b))
        if n1 == 0 or n2 == 0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (n1 * n2)

    def search(self, query: list[float], top: int = 10, threshold: float = 0.0) -> list[tuple[str, float]]:
        ef = max(self.ef_construction, top)
        candidates = [(self._cosine(query, v), vid) for vid, v in self.vectors.items()]
        candidates.sort(reverse=True)
        return [(vid, s) for vid, s in candidates if s >= threshold][:top]

    def count(self) -> int:
        return len(self.vectors)
