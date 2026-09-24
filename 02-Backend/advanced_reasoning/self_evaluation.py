from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass
class EvaluationResult:
    score: float
    dimensions: Dict[str, float]
    suggestions: List[str]
    confidence: float = 1.0


class SelfEvaluator:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "coherence": 0.3,
            "accuracy": 0.3,
            "completeness": 0.2,
            "conciseness": 0.1,
            "tone": 0.1,
        }

    def evaluate(self, response: str, context: str, expected: Optional[str] = None) -> EvaluationResult:
        dims = {
            "coherence": self._score_coherence(response),
            "accuracy": self._score_accuracy(response, expected) if expected else 0.7,
            "completeness": self._score_completeness(response, context),
            "conciseness": self._score_conciseness(response),
            "tone": self._score_tone(response),
        }
        score = sum(dims[k] * self.weights.get(k, 0.0) for k in dims)
        suggestions = self._generate_suggestions(dims, response)
        confidence = self._estimate_confidence(dims)
        return EvaluationResult(score=score, dimensions=dims, suggestions=suggestions, confidence=confidence)

    def _score_coherence(self, text: str) -> float:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if len(sentences) < 2:
            return 0.5
        words = text.split()
        ttr = len(set(words)) / max(len(words), 1)
        return min(1.0, 0.4 + ttr * 0.6)

    def _score_accuracy(self, response: str, expected: Optional[str]) -> float:
        if not expected:
            return 0.7
        r_words = set(response.lower().split())
        e_words = set(expected.lower().split())
        if not e_words:
            return 0.5
        overlap = len(r_words & e_words) / len(e_words)
        return min(1.0, 0.3 + overlap * 0.7)

    def _score_completeness(self, response: str, context: str) -> float:
        if not context:
            return 0.6
        ctx_words = set(context.lower().split())
        resp_words = set(response.lower().split())
        if not ctx_words:
            return 0.6
        coverage = len(ctx_words & resp_words) / len(ctx_words)
        return min(1.0, 0.3 + coverage * 0.7)

    def _score_conciseness(self, text: str) -> float:
        words = len(text.split())
        if words == 0:
            return 0.0
        if words <= 50:
            return 1.0
        if words <= 200:
            return 0.8
        if words <= 500:
            return 0.5
        return 0.2

    def _score_tone(self, text: str) -> float:
        positive = ["helpful", "great", "excellent", "thank", "please", "welcome"]
        negative = ["stupid", "idiot", "hate", "terrible", "worst", "useless"]
        lower = text.lower()
        pos = sum(lower.count(w) for w in positive)
        neg = sum(lower.count(w) for w in negative)
        if pos + neg == 0:
            return 0.75
        return max(0.0, min(1.0, 0.5 + (pos - neg) / (pos + neg) * 0.5))

    def _generate_suggestions(self, dims: Dict[str, float], text: str) -> List[str]:
        suggestions = []
        for dim, val in dims.items():
            if val < 0.6:
                suggestions.append(f"Improve {dim}: current score {val:.2f}")
        if len(text.split()) > 300:
            suggestions.append("Consider making the response more concise")
        return suggestions

    def _estimate_confidence(self, dims: Dict[str, float]) -> float:
        values = np.array(list(dims.values()))
        return float(1.0 - np.std(values))
