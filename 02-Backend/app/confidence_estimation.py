"""Confidence estimation for tools, retrieval, and memory."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceEstimate:
    score: float
    rationale: str
    factors: dict[str, float]


class ConfidenceEstimator:
    def estimate_tool_confidence(self, tool_name: str, result: Any, latency_ms: float, success: bool) -> ConfidenceEstimate:
        score = 1.0 if success else 0.0
        if success and latency_ms > 5000:
            score -= 0.2
        if success and latency_ms > 10000:
            score -= 0.3
        score = max(0.0, min(1.0, score))
        return ConfidenceEstimate(
            score=score,
            rationale="success and latency based",
            factors={"success": float(success), "latency_ms": latency_ms},
        )

    def estimate_retrieval_confidence(self, scores: list[float], coverage: float) -> ConfidenceEstimate:
        if not scores:
            return ConfidenceEstimate(score=0.0, rationale="no_results", factors={})
        avg_score = sum(scores) / len(scores)
        score = min(1.0, avg_score * coverage)
        return ConfidenceEstimate(
            score=score,
            rationale="mean similarity * coverage",
            factors={"mean_score": avg_score, "coverage": coverage},
        )

    def estimate_memory_confidence(self, memory_age_days: float, access_count: int, source_reliability: float) -> ConfidenceEstimate:
        recency = max(0.0, 1.0 - (memory_age_days / 365.0))
        score = (recency * 0.4) + (min(1.0, access_count / 100.0) * 0.3) + (source_reliability * 0.3)
        return ConfidenceEstimate(
            score=score,
            rationale="weighted recency, usage, and source reliability",
            factors={"recency": recency, "usage": min(1.0, access_count / 100.0), "source": source_reliability},
        )
