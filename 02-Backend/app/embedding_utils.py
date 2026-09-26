"""Embedding normalization utilities."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NormalizedEmbedding:
    vector: list[float]
    original_norm: float
    normalized_norm: float
    dimension: int


class EmbeddingNormalizationHelper:
    @staticmethod
    def normalize(vector: list[float], eps: float = 1e-12) -> NormalizedEmbedding:
        if not vector:
            return NormalizedEmbedding(vector=[], original_norm=0.0, normalized_norm=0.0, dimension=0)
        norm = math.sqrt(sum(x * x for x in vector))
        original_norm = norm
        if norm < eps:
            return NormalizedEmbedding(
                vector=[0.0] * len(vector),
                original_norm=original_norm,
                normalized_norm=0.0,
                dimension=len(vector),
            )
        normalized = [x / norm for x in vector]
        return NormalizedEmbedding(
            vector=normalized,
            original_norm=original_norm,
            normalized_norm=1.0,
            dimension=len(vector),
        )

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def euclidean_distance(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return float("inf")
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    @staticmethod
    def batch_normalize(vectors: list[list[float]], eps: float = 1e-12) -> list[NormalizedEmbedding]:
        return [EmbeddingNormalizationHelper.normalize(v, eps=eps) for v in vectors]

    @staticmethod
    def to_unit_sphere(vector: list[float]) -> list[float]:
        return EmbeddingNormalizationHelper.normalize(vector).vector
