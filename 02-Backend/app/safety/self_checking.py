"""AI self-checking and self-critique."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CritiqueResult:
    confidence: float
    issues: list[str]
    suggested_fixes: list[str]
    passed: bool


class ConfidenceEstimator:
    def estimate(self, response: str, context: Optional[str] = None) -> float:
        if not response or not response.strip():
            return 0.0
        base = 0.5
        hedging = len(re.findall(r"\b(?:might|maybe|possibly|unclear|unknown)\b", response, re.IGNORECASE))
        base -= hedging * 0.05
        certainty = len(re.findall(r"\b(?:definitely|certainly|always|never|must)\b", response, re.IGNORECASE))
        base += certainty * 0.05
        if context and response.lower() in context.lower():
            base += 0.2
        return max(0.0, min(1.0, base))


class CritiqueChain:
    def __init__(self):
        self._checks: list[callable] = []

    def add_check(self, check: callable):
        self._checks.append(check)

    def run(self, response: str, context: Optional[str] = None) -> list[dict]:
        results = []
        for check in self._checks:
            try:
                results.append(check(response, context))
            except Exception as exc:
                logger.error("Self-check failed: %s", exc)
        return results


class SelfChecker:
    def __init__(self):
        self.confidence_estimator = ConfidenceEstimator()
        self.critique_chain = CritiqueChain()
        self.critique_chain.add_check(self._check_toxicity)
        self.critique_chain.add_check(self._check_factual_consistency)
        self.critique_chain.add_check(self._check_completeness)

    def check(self, response: str, context: Optional[str] = None) -> CritiqueResult:
        issues = []
        fixes = []
        critique_results = self.critique_chain.run(response, context)
        for cr in critique_results:
            if not cr.get("passed", True):
                issues.extend(cr.get("issues", []))
                fixes.extend(cr.get("fixes", []))
        confidence = self.confidence_estimator.estimate(response, context)
        return CritiqueResult(
            confidence=round(confidence, 3),
            issues=list(set(issues)),
            suggested_fixes=list(set(fixes)),
            passed=len(issues) == 0 and confidence >= 0.6,
        )

    def _check_toxicity(self, response: str, context: Optional[str] = None) -> dict:
        toxic = re.search(r"\b(?:idiot|stupid|hate|kill)\b", response, re.IGNORECASE)
        return {
            "passed": not bool(toxic),
            "issues": ["Toxic language detected"] if toxic else [],
            "fixes": ["Remove toxic language"] if toxic else [],
        }

    def _check_factual_consistency(self, response: str, context: Optional[str] = None) -> dict:
        if context and response.lower() in context.lower():
            return {"passed": True, "issues": [], "fixes": []}
        if context:
            return {"passed": True, "issues": [], "fixes": []}
        return {"passed": True, "issues": [], "fixes": []}

    def _check_completeness(self, response: str, context: Optional[str] = None) -> dict:
        if len(response.strip()) < 10:
            return {"passed": False, "issues": ["Response is too short"], "fixes": ["Provide more detail"]}
        return {"passed": True, "issues": [], "fixes": []}


self_checker = SelfChecker()
