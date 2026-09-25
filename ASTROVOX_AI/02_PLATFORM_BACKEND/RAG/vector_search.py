"""RAG: dense vector search skeleton."""

from __future__ import annotations

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class VectorSearch:
    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension
        self._embeddings: List[List[float]] = []
        self._documents: List[str] = []

    def index(self, documents: List[str], embeddings: List[List[float]]) -> None:
        self._documents = documents
        self._embeddings = embeddings

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Tuple[int, float]]:
        scores = []
        for idx, embedding in enumerate(self._embeddings):
            score = self._cosine_similarity(query_embedding, embedding)
            scores.append((idx, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
