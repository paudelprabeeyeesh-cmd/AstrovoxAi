import logging
import re

logger = logging.getLogger(__name__)

_MIN_PROMPT_WORDS = 3
_MAX_PROMPT_WORDS = 500
_CLARITY_STOP_WORDS = {
    "um", "uh", "like", "basically", "actually", "literally", "stuff", "thing",
}


class PromptEvaluator:
    def __init__(self):
        self.results = []

    def evaluate(self, prompt: str) -> dict:
        prompt = prompt.strip()
        scores = {
            "length": self._score_length(prompt),
            "clarity": self._score_clarity(prompt),
            "specificity": self._score_specificity(prompt),
            "safety": self._score_safety(prompt),
        }
        overall = round(sum(scores.values()) / len(scores), 3)
        result = {"prompt": prompt, "scores": scores, "overall": overall}
        self.results.append(result)
        return result

    def _score_length(self, prompt: str) -> float:
        words = prompt.split()
        if not words:
            return 0.0
        count = len(words)
        if count < _MIN_PROMPT_WORDS:
            return max(0.0, count / _MIN_PROMPT_WORDS)
        if count > _MAX_PROMPT_WORDS:
            return max(0.0, 1.0 - (count - _MAX_PROMPT_WORDS) / _MAX_PROMPT_WORDS)
        return 1.0

    def _score_clarity(self, prompt: str) -> float:
        words = [w.lower() for w in prompt.split()]
        if not words:
            return 0.0
        stop_hits = sum(1 for w in words if w in _CLARITY_STOP_WORDS)
        base = 1.0 - (stop_hits / len(words))
        if "?" in prompt:
            base += 0.1
        return min(1.0, max(0.0, base))

    def _score_specificity(self, prompt: str) -> float:
        words = set(re.findall(r"[a-zA-Z]+", prompt.lower()))
        if not words:
            return 0.0
        specific = {"list", "explain", "compare", "summarize", "analyze", "step", "why", "how"}
        hit = sum(1 for w in words if w in specific)
        return min(1.0, hit / max(1, len(specific)))

    def _score_safety(self, prompt: str) -> float:
        injection_patterns = [
            r"ignore\s+(previous|above|all)\s+instructions?",
            r"you\s+are\s+now\s+(a\s+)?different",
            r"disregard\s+all\s+prior",
            r"jailbreak",
            r"DAN\s+mode",
            r"pretend\s+to\s+be",
            r"bypass\s+filter",
        ]
        lower = prompt.lower()
        for pattern in injection_patterns:
            if re.search(pattern, lower):
                return 0.0
        return 1.0

    def aggregate(self) -> dict:
        if not self.results:
            return {"count": 0, "avg_overall": 0.0}
        scores = {"length": 0.0, "clarity": 0.0, "specificity": 0.0, "safety": 0.0}
        for r in self.results:
            for k in scores:
                scores[k] += r["scores"][k]
        n = len(self.results)
        return {
            "count": n,
            "avg_overall": round(sum(r["overall"] for r in self.results) / n, 3),
            "avg_length": round(scores["length"] / n, 3),
            "avg_clarity": round(scores["clarity"] / n, 3),
            "avg_specificity": round(scores["specificity"] / n, 3),
            "avg_safety": round(scores["safety"] / n, 3),
        }
