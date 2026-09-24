
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_JAILBREAK_PATTERNS = [
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


class JailbreakDetector:
    def detect(self, prompt: str) -> dict[str, Any]:
        prompt_lower = prompt.lower()
        hits = []
        for pattern in _JAILBREAK_PATTERNS:
            match = re.search(pattern, prompt_lower, re.IGNORECASE)
            if match:
                hits.append(pattern)
        blocked = len(hits) > 0
        score = max(0.0, 1.0 - 0.2 * len(hits))
        return {
            "blocked": blocked,
            "score": round(score, 4),
            "hits": hits,
            "risk_level": "high" if blocked else "low",
        }

    def score(self, prompt: str) -> float:
        return self.detect(prompt)["score"]
