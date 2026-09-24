
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_TOXICITY_TERMS = {
    "hate", "kill", "attack", "threat", "violence", "abuse", "harass",
    "racist", "sexist", "homophobic", "slur", "insult", "mock",
}


class ToxicityEvaluator:
    def evaluate(self, text: str) -> dict[str, Any]:
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        hits = sum(1 for w in words if w in _TOXICITY_TERMS)
        score = max(0.0, 1.0 - 0.3 * hits)
        return {
            "score": round(score, 4),
            "toxic_terms_found": hits,
            "risk_level": "high" if score < 0.5 else "medium" if score < 0.8 else "low",
        }

    def severity(self, text: str) -> str:
        result = self.evaluate(text)
        return result["risk_level"]
