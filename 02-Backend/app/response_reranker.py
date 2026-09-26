"""Response reranking step for improving inference quality."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RankedResponse:
    content: str
    score: float
    rank: int
    metadata: dict = field(default_factory=dict)


class ResponseReranker:
    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = weights or {
            "relevance": 0.4,
            "coherence": 0.2,
            "length": 0.1,
            "freshness": 0.1,
            "diversity": 0.2,
        }

    def rerank(
        self,
        responses: list[str],
        prompt: str = "",
        context: Optional[str] = None,
    ) -> list[RankedResponse]:
        if not responses:
            return []
        scored = []
        prompt_words = set(prompt.lower().split()) if prompt else set()
        for idx, resp in enumerate(responses):
            scores = {
                "relevance": self._score_relevance(resp, prompt_words),
                "coherence": self._score_coherence(resp),
                "length": self._score_length(resp),
                "freshness": 1.0,
                "diversity": self._score_diversity(resp, [r for i, r in enumerate(responses) if i != idx]),
            }
            total = sum(self.weights.get(k, 0.0) * v for k, v in scores.items())
            scored.append(RankedResponse(
                content=resp,
                score=round(total, 4),
                rank=0,
                metadata={"factor_scores": scores},
            ))
        scored.sort(key=lambda r: r.score, reverse=True)
        for i, item in enumerate(scored):
            item.rank = i + 1
        return scored

    def _score_relevance(self, response: str, prompt_words: set) -> float:
        if not prompt_words:
            return 0.7
        resp_words = set(response.lower().split())
        overlap = len(prompt_words & resp_words)
        return min(1.0, 0.3 + (overlap / max(len(prompt_words), 1)) * 0.7)

    def _score_coherence(self, response: str) -> float:
        sentences = response.split(".")
        if not sentences:
            return 0.0
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len < 3:
            return 0.3
        if avg_len > 60:
            return 0.5
        return 0.85

    def _score_length(self, response: str) -> float:
        words = len(response.split())
        if words == 0:
            return 0.0
        if words < 10:
            return 0.4
        if words < 500:
            return 0.9
        return 0.6 if words > 2000 else 0.8

    def _score_diversity(self, response: str, other_responses: list[str]) -> float:
        if not other_responses:
            return 1.0
        resp_lower = response.lower()
        for other in other_responses:
            other_lower = other.lower()
            similarity = len(set(resp_lower.split()) & set(other_lower.split())) / max(len(set(resp_lower.split())), 1)
            if similarity > 0.8:
                return 0.3
        return 1.0

    def top(self, responses: list[str], prompt: str = "", context: Optional[str] = None, n: int = 1) -> list[RankedResponse]:
        ranked = self.rerank(responses, prompt=prompt, context=context)
        return ranked[:n]
