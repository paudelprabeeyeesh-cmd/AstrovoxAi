import logging
import math
import random
import re

logger = logging.getLogger(__name__)


class CapabilityEvaluator:
    def __init__(self):
        self.results = []

    def evaluate(self, task_type: str, response: str, reference: str) -> dict:
        response = response.strip()
        reference = reference.strip()
        scores = {
            "fluency": self._score_fluency(response),
            "relevance": self._score_relevance(response, reference),
            "factuality": self._score_factuality(response, reference),
        }
        overall = round(sum(scores.values()) / len(scores), 3)
        result = {"task_type": task_type, "scores": scores, "overall": overall}
        self.results.append(result)
        return result

    def _score_fluency(self, text: str) -> float:
        if not text:
            return 0.0
        words = text.split()
        if not words:
            return 0.0
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len < 2 or avg_len > 15:
            return 0.5
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            return 0.7
        return 1.0 if len(sentences) >= 1 else 0.5

    def _score_relevance(self, response: str, reference: str) -> float:
        if not reference:
            return 1.0 if response else 0.0
        ref_terms = set(reference.lower().split())
        if not ref_terms:
            return 1.0
        resp_terms = set(response.lower().split())
        overlap = len(ref_terms & resp_terms)
        return min(1.0, overlap / len(ref_terms))

    def _score_factuality(self, response: str, reference: str) -> float:
        if not reference:
            return 1.0
        ref_words = set(reference.lower().split())
        resp_words = set(response.lower().split())
        if not ref_words:
            return 1.0
        overlap = len(ref_words & resp_words)
        return min(1.0, overlap / max(1, len(ref_words) * 0.5))

    def aggregate(self) -> dict:
        if not self.results:
            return {"count": 0, "avg_overall": 0.0}
        scores = {"fluency": 0.0, "relevance": 0.0, "factuality": 0.0}
        for r in self.results:
            for k in scores:
                scores[k] += r["scores"][k]
        n = len(self.results)
        return {
            "count": n,
            "avg_overall": round(sum(r["overall"] for r in self.results) / n, 3),
            "avg_fluency": round(scores["fluency"] / n, 3),
            "avg_relevance": round(scores["relevance"] / n, 3),
            "avg_factuality": round(scores["factuality"] / n, 3),
        }
