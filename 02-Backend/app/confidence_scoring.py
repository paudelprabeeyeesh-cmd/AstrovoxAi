"""Confidence scoring wrapper for inference responses."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceScore:
    score: float
    label: str
    factors: dict[str, float] = field(default_factory=dict)
    recommendation: str = ""


class ConfidenceScoringWrapper:
    FACTOR_WEIGHTS = {
        "length": 0.1,
        "coherence": 0.2,
        "specificity": 0.25,
        "certainty": 0.25,
        "consistency": 0.2,
    }

    def score_response(
        self,
        response: str,
        prompt: str = "",
        context: Optional[str] = None,
        tool_calls: Optional[list[dict]] = None,
    ) -> ConfidenceScore:
        factors: dict[str, float] = {}
        factors["length"] = self._score_length(response)
        factors["coherence"] = self._score_coherence(response)
        factors["specificity"] = self._score_specificity(response)
        factors["certainty"] = self._score_certainty(response)
        factors["consistency"] = self._score_consistency(response, prompt)
        weighted = sum(factors[k] * self.FACTOR_WEIGHTS[k] for k in factors)
        score = max(0.0, min(1.0, weighted))
        label = self._classify(score)
        recommendation = self._recommend(score, factors)
        return ConfidenceScore(
            score=round(score, 3),
            label=label,
            factors=factors,
            recommendation=recommendation,
        )

    def _score_length(self, response: str) -> float:
        words = len(response.split())
        if words == 0:
            return 0.0
        if words < 5:
            return 0.2
        if words < 20:
            return 0.5
        if words < 200:
            return 0.8
        return 0.6 if words > 1000 else 0.9

    def _score_coherence(self, response: str) -> float:
        sentences = re.split(r"[.!?]+", response)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg_len < 3:
            return 0.4
        if avg_len > 50:
            return 0.5
        return 0.9

    def _score_specificity(self, response: str) -> float:
        score = 0.5
        if re.search(r"\b\d{4}\b", response):
            score += 0.1
        if re.search(r"\$[\d,]+", response):
            score += 0.1
        if re.search(r"\b\d+%\b", response):
            score += 0.1
        if re.search(r"\b(?:according to|specifically|for example|for instance)\b", response, re.I):
            score += 0.1
        if re.search(r"\b(?:in general|usually|typically|often)\b", response, re.I):
            score -= 0.1
        return max(0.0, min(1.0, score))

    def _score_certainty(self, response: str) -> float:
        lower = response.lower()
        certainty = 0.5
        high = [r"\bdefinitely\b", r"\babsolutely\b", r"\bconfirmed\b", r"\bproven\b"]
        low = [r"\bmight\b", r"\bperhaps\b", r"\bpossibly\b", r"\bi think\b", r"\bmaybe\b"]
        for p in high:
            if re.search(p, lower):
                certainty += 0.15
        for p in low:
            if re.search(p, lower):
                certainty -= 0.15
        return max(0.0, min(1.0, certainty))

    def _score_consistency(self, response: str, prompt: str) -> float:
        if not prompt:
            return 0.7
        prompt_words = set(re.findall(r"\b\w+\b", prompt.lower()))
        response_words = set(re.findall(r"\b\w+\b", response.lower()))
        if not prompt_words:
            return 0.7
        overlap = len(prompt_words & response_words) / len(prompt_words)
        return min(1.0, 0.5 + overlap)

    def _classify(self, score: float) -> str:
        if score >= 0.8:
            return "high"
        if score >= 0.6:
            return "medium"
        if score >= 0.4:
            return "low"
        return "very_low"

    def _recommend(self, score: float, factors: dict[str, float]) -> str:
        if score >= 0.8:
            return "response is reliable"
        weak = [k for k, v in factors.items() if v < 0.5]
        if weak:
            return f"consider retrying or grounding; weak factors: {', '.join(weak)}"
        return "acceptable but could be improved"

    def wrap(self, response: str, prompt: str = "", context: Optional[str] = None) -> dict[str, Any]:
        score = self.score_response(response, prompt=prompt, context=context)
        return {
            "response": response,
            "confidence": score.score,
            "confidence_label": score.label,
            "confidence_factors": score.factors,
            "recommendation": score.recommendation,
        }
