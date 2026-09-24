import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_TOXICITY_TERMS = {
    "severe_toxic": ["hate", "kill", "destroy", "murder", "terrorist"],
    "threat": ["hurt", "attack", "danger", "threaten", "assault"],
    "insult": ["stupid", "idiot", "dumb", "fool", "moron"],
    "obscene": ["damn", "hell", "crap"],
    "identity_hate": ["racist", "sexist", "discriminate", "bigot", "supremacist"],
}
_ALL_TOXIC_TERMS = set(term for terms in _TOXICITY_TERMS.values() for term in terms)


class ToxicityEvaluator:
    def evaluate(self, text: str) -> dict[str, Any]:
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        category_scores = {}
        for category, keywords in _TOXICITY_TERMS.items():
            hits = sum(1 for w in words if w in keywords)
            category_scores[category] = min(1.0, hits * 0.3)
        toxic_score = category_scores.get("severe_toxic", 0.0) * 1.5 + category_scores.get("threat", 0.0) + category_scores.get("insult", 0.0) * 0.5
        toxic_score = min(1.0, toxic_score)
        if toxic_score >= 0.7:
            label = "severe_toxic"
        elif toxic_score >= 0.4:
            label = "toxic"
        else:
            label = "clean"
        return {
            "score": round(toxic_score, 4),
            "label": label,
            "toxic_terms_found": sum(1 for w in words if w in _ALL_TOXIC_TERMS),
            "category_scores": {k: round(v, 4) for k, v in category_scores.items()},
            "risk_level": "high" if toxic_score >= 0.7 else "medium" if toxic_score >= 0.4 else "low",
        }

    def severity(self, text: str) -> str:
        return self.evaluate(text)["risk_level"]

    def batch_evaluate(self, texts: list[str]) -> list[dict[str, Any]]:
        return [self.evaluate(text) for text in texts]
