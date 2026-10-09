import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_CLAIM_INDICATORS = [
    "always", "never", "definitely", "certainly", "guaranteed",
    "all", "none", "every", "no one", "impossible", "must",
    "proven", "fact", "truth", "undoubtedly", "absolutely",
]
_NUMERIC_CLAIM_PATTERNS = [
    r"\b\d+(\.\d+)?%?\b",
    r"\$\d+",
    r"\b\d{4}\b",
]


class HallucinationDetector:
    def detect(self, output: str, context: str = "") -> dict[str, Any]:
        output_lower = output.lower()
        words = output.split()
        claims = [w for w in words if w.lower().strip(".,!?;:") in _CLAIM_INDICATORS]
        claim_density = len(claims) / max(len(words), 1)
        unsupported_claims = 0
        if context:
            context_lower = context.lower()
            for claim in claims:
                if claim.lower().strip(".,!?;:") not in context_lower:
                    unsupported_claims += 1
        numeric_claims = []
        for pattern in _NUMERIC_CLAIM_PATTERNS:
            numeric_claims.extend(re.findall(pattern, output))
        unsupported_numerics = 0
        if context:
            context_lower = context.lower()
            for claim in numeric_claims:
                if str(claim) not in context_lower:
                    unsupported_numerics += 1
        hallucination_score = min(1.0, claim_density * 2.0 + (unsupported_claims / max(len(claims), 1)) * 0.5 + unsupported_numerics * 0.1)
        risk_level = "high" if hallucination_score > 0.6 else "medium" if hallucination_score > 0.3 else "low"
        return {
            "score": round(hallucination_score, 4),
            "claims_found": claims,
            "unsupported_claims": unsupported_claims,
            "numeric_claims": numeric_claims,
            "unsupported_numeric_claims": unsupported_numerics,
            "claim_density": round(claim_density, 4),
            "risk_level": risk_level,
        }

    def faithfulness(self, output: str, context: str) -> float:
        result = self.detect(output, context)
        return round(1.0 - result["score"], 4)

    def factuality_score(self, output: str, reference: str) -> float:
        if not reference:
            return 1.0
        output_terms = set(output.lower().split())
        reference_terms = set(reference.lower().split())
        if not reference_terms:
            return 1.0
        overlap = output_terms & reference_terms
        return round(len(overlap) / len(reference_terms), 4)
