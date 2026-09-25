import logging
from typing import Any

logger = logging.getLogger(__name__)


class HallucinationDetector:
    def detect(self, output: str, context: str) -> dict[str, Any]:
        words = output.split()
        claim_indicators = ["always", "never", "definitely", "certainly", "guaranteed"]
        claims = [w for w in words if w.lower() in claim_indicators]
        score = min(len(claims) / max(len(words), 1) * 10, 1.0)
        return {
            "score": score,
            "claims_found": claims,
            "risk_level": "high" if score > 0.5 else "low",
        }
