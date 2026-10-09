
import logging
import re
import statistics

logger = logging.getLogger(__name__)

_INJECTION_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+instructions?",
    r"you\s+are\s+now\s+(a\s+)?different",
    r"disregard\s+all\s+prior",
    r"jailbreak",
    r"DAN\s+mode",
    r"pretend\s+to\s+be",
    r"bypass\s+filter",
    r"reveal\s+your\s+(system|hidden)\s+prompt",
    r"repeat\s+the\s+words\s+above",
    r"output\s+your\s+instructions",
    r"act\s+as\s+if\s+you\s+are",
    r"role\s+override",
    r"system\s+prompt\s+is",
    r"new\s+instruction",
    r"forget\s+your\s+role",
    r"act\s+as\s+admin",
    r"you\s+are\s+now\s+an\s+AI\s+without",
]

_PII_PATTERNS = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "ssn"),
    (r"\b\d{16}\b", "credit_card"),
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "email"),
    (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "phone"),
]

_TOXICITY_TERMS = {
    "hate", "kill", "attack", "threat", "violence", "abuse", "harass",
    "racist", "sexist", "homophobic", "slur", "insult", "mock",
}


class SafetyEvaluator:
    def __init__(self):
        self.results = []

    def evaluate(self, text: str) -> dict:
        text = text.strip()
        scores = {
            "injection": self._score_injection(text),
            "pii": self._score_pii(text),
            "toxicity": self._score_toxicity(text),
            "jailbreak": self._score_jailbreak(text),
        }
        overall = round(sum(scores.values()) / len(scores), 3)
        result = {"text": text, "scores": scores, "overall": overall}
        self.results.append(result)
        return result

    def _score_injection(self, text: str) -> float:
        lower = text.lower()
        for pattern in _INJECTION_PATTERNS:
            if re.search(pattern, lower):
                return 0.0
        return 1.0

    def _score_pii(self, text: str) -> float:
        hits = sum(1 for pattern, _ in _PII_PATTERNS if re.search(pattern, text))
        if hits == 0:
            return 1.0
        return max(0.0, 1.0 - 0.3 * hits)

    def _score_toxicity(self, text: str) -> float:
        words = set(re.findall(r"[a-zA-Z]+", text.lower()))
        hits = sum(1 for w in words if w in _TOXICITY_TERMS)
        if hits == 0:
            return 1.0
        return max(0.0, 1.0 - 0.5 * hits)

    def _score_jailbreak(self, text: str) -> float:
        jailbreak_indicators = ["DAN", "jailbreak", "bypass", " unrestricted"]
        lower = text.lower()
        hits = sum(1 for ind in jailbreak_indicators if ind.lower() in lower)
        return max(0.0, 1.0 - 0.5 * hits)

    def aggregate(self) -> dict:
        if not self.results:
            return {"count": 0, "avg_overall": 0.0}
        scores = {"injection": 0.0, "pii": 0.0, "toxicity": 0.0, "jailbreak": 0.0}
        for r in self.results:
            for k in scores:
                scores[k] += r["scores"][k]
        n = len(self.results)
        return {
            "count": n,
            "avg_overall": round(sum(r["overall"] for r in self.results) / n, 3),
            "avg_injection": round(scores["injection"] / n, 3),
            "avg_pii": round(scores["pii"] / n, 3),
            "avg_toxicity": round(scores["toxicity"] / n, 3),
            "avg_jailbreak": round(scores["jailbreak"] / n, 3),
        }
