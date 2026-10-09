from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SimilarityResult:
    score: float
    method: str
    details: Dict[str, Any] = field(default_factory=dict)


class SimilarityEstimator:
    def __init__(self, method: str = "cosine") -> None:
        self.method = method
        self.history: List[SimilarityResult] = []

    def _validate(self, a: List[float], b: List[float]) -> None:
        if len(a) != len(b):
            raise ValueError("Vectors must have the same length")
        if not a:
            raise ValueError("Vectors must not be empty")

    def cosine(self, a: List[float], b: List[float]) -> SimilarityResult:
        self._validate(a, b)
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        denom = norm_a * norm_b
        score = dot / denom if denom > 0 else 0.0
        result = SimilarityResult(score=score, method="cosine", details={"dot": dot, "norm_a": norm_a, "norm_b": norm_b})
        self.history.append(result)
        return result

    def euclidean(self, a: List[float], b: List[float]) -> SimilarityResult:
        self._validate(a, b)
        dist = sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5
        score = 1.0 / (1.0 + dist)
        result = SimilarityResult(score=score, method="euclidean", details={"distance": dist})
        self.history.append(result)
        return result

    def manhattan(self, a: List[float], b: List[float]) -> SimilarityResult:
        self._validate(a, b)
        dist = sum(abs(x - y) for x, y in zip(a, b))
        score = 1.0 / (1.0 + dist)
        result = SimilarityResult(score=score, method="manhattan", details={"distance": dist})
        self.history.append(result)
        return result

    def pearson(self, a: List[float], b: List[float]) -> SimilarityResult:
        self._validate(a, b)
        n = len(a)
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
        den_a = sum((a[i] - mean_a) ** 2 for i in range(n)) ** 0.5
        den_b = sum((b[i] - mean_b) ** 2 for i in range(n)) ** 0.5
        denom = den_a * den_b
        score = num / denom if denom > 0 else 0.0
        result = SimilarityResult(score=score, method="pearson", details={"n": n})
        self.history.append(result)
        return result

    def jaccard(self, a: List[float], b: List[float]) -> SimilarityResult:
        self._validate(a, b)
        intersection = sum(1 for x, y in zip(a, b) if x > 0 and y > 0)
        union = sum(1 for x, y in zip(a, b) if x > 0 or y > 0)
        score = intersection / union if union > 0 else 0.0
        result = SimilarityResult(score=score, method="jaccard", details={"intersection": intersection, "union": union})
        self.history.append(result)
        return result

    def estimate(
        self,
        a: List[float],
        b: List[float],
        method: Optional[str] = None,
    ) -> SimilarityResult:
        chosen = method or self.method
        if chosen == "cosine":
            return self.cosine(a, b)
        if chosen == "euclidean":
            return self.euclidean(a, b)
        if chosen == "manhattan":
            return self.manhattan(a, b)
        if chosen == "pearson":
            return self.pearson(a, b)
        if chosen == "jaccard":
            return self.jaccard(a, b)
        raise ValueError(f"Unknown similarity method '{chosen}'")

    def summary(self) -> Dict[str, Any]:
        if not self.history:
            return {"count": 0}
        scores = [r.score for r in self.history]
        return {
            "count": len(scores),
            "mean_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "last_score": scores[-1],
        }
