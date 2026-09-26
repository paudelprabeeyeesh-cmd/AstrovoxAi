"""AI self-checking for output validation."""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CritiqueType(Enum):
    FACTUALITY = "factuality"
    COHERENCE = "coherence"
    SAFETY = "safety"
    RELEVANCE = "relevance"
    HALLUCINATION = "hallucination"
    BIAS = "bias"
    TOXICITY = "toxicity"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    PRIVACY = "privacy"


class Severity(Enum):
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CritiqueResult:
    passed: bool
    critiques: List[Dict[str, Any]] = field(default_factory=list)
    overall_score: float = 1.0
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfChecker:
    HALLUCINATION_PATTERNS = [
        re.compile(r"\b(?:I think|I believe|probably|maybe|possibly|might have|could be)\b", re.IGNORECASE),
        re.compile(r"\b(?:according to|based on|studies show|experts say|research indicates)\b", re.IGNORECASE),
        re.compile(r"\b(?:approximately|around|roughly|about)\b \d+", re.IGNORECASE),
    ]

    FACTUALITY_INDICATORS = [
        re.compile(r"\b(?:in fact|actually|obviously|clearly|without a doubt|undoubtedly)\b", re.IGNORECASE),
        re.compile(r"\b(?:all|every|always|never|none|no one|nobody|nothing)\b", re.IGNORECASE),
    ]

    BIAS_PATTERNS = [
        re.compile(r"\b(?:women|men|blacks|whites|asians|latinos)\b.*\b(?:always|never|all|none)\b", re.IGNORECASE),
        re.compile(r"\b(?:bad at|good at|worse at|better at)\b.*\b(?:math|science|sports|driving)\b", re.IGNORECASE),
    ]

    TOXICITY_PATTERNS = [
        re.compile(r"\b(?:stupid|idiot|moron|dumb|ignorant|fool)\b", re.IGNORECASE),
        re.compile(r"\b(?:shut up|go away|leave|get lost|get out)\b", re.IGNORECASE),
    ]

    PRIVACY_PATTERNS = [
        re.compile(r"\b(?:password|secret|api[_\s-]?key|token|private)\s*(?:key|is|=|:)\b", re.IGNORECASE),
        re.compile(r"\b(?:social security number|ssn|credit card|cvv|expiry)\b", re.IGNORECASE),
    ]

    def __init__(self):
        self._checks = {
            CritiqueType.FACTUALITY: self._check_factuality,
            CritiqueType.HALLUCINATION: self._check_hallucination,
            CritiqueType.BIAS: self._check_bias,
            CritiqueType.TOXICITY: self._check_toxicity,
            CritiqueType.PRIVACY: self._check_privacy,
            CritiqueType.COHERENCE: self._check_coherence,
            CritiqueType.SAFETY: self._check_safety,
            CritiqueType.COMPLETENESS: self._check_completeness,
        }

    def check(self, text: str, context: Optional[str] = None) -> CritiqueResult:
        critiques: List[Dict[str, Any]] = []
        all_passed = True

        for check_type, check_fn in self._checks.items():
            passed, details = check_fn(text, context=context)
            if not passed:
                all_passed = False
                critiques.append({
                    "type": check_type.value,
                    "passed": passed,
                    "severity": details.get("severity", Severity.WARNING.value),
                    "evidence": details.get("evidence", ""),
                    "details": details,
                })

        score = self._compute_score(critiques)
        summary = self._summarize(critiques, score)

        return CritiqueResult(
            passed=all_passed,
            critiques=critiques,
            overall_score=score,
            summary=summary,
        )

    def _check_factuality(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        hits = sum(1 for p in self.FACTUALITY_INDICATORS if p.search(text))
        if hits > 2:
            return False, {
                "severity": Severity.WARNING.value,
                "evidence": f"Absolute claims detected ({hits})",
                "absolute_claims": hits,
            }
        return True, {"absolute_claims": hits}

    def _check_hallucination(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        hits = sum(1 for p in self.HALLUCINATION_PATTERNS if p.search(text))
        if hits > 3:
            return False, {
                "severity": Severity.ERROR.value,
                "evidence": f"Possible hallucination indicators ({hits})",
                "hallucination_signals": hits,
            }
        return True, {"hallucination_signals": hits}

    def _check_bias(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        hits = sum(1 for p in self.BIAS_PATTERNS if p.search(text))
        if hits > 0:
            return False, {
                "severity": Severity.WARNING.value,
                "evidence": f"Bias patterns detected ({hits})",
                "bias_signals": hits,
            }
        return True, {"bias_signals": hits}

    def _check_toxicity(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        hits = sum(1 for p in self.TOXICITY_PATTERNS if p.search(text))
        if hits > 0:
            return False, {
                "severity": Severity.ERROR.value,
                "evidence": f"Toxic language detected ({hits})",
                "toxic_signals": hits,
            }
        return True, {"toxic_signals": hits}

    def _check_privacy(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        hits = sum(1 for p in self.PRIVACY_PATTERNS if p.search(text))
        if hits > 0:
            return False, {
                "severity": Severity.CRITICAL.value,
                "evidence": f"Privacy violation signals ({hits})",
                "privacy_signals": hits,
            }
        return True, {"privacy_signals": hits}

    def _check_coherence(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1) if sentences else 0
        if len(sentences) > 1 and avg_len < 5:
            return False, {
                "severity": Severity.INFO.value,
                "evidence": "Very short sentences detected",
                "avg_sentence_length": avg_len,
            }
        return True, {"avg_sentence_length": avg_len, "sentence_count": len(sentences)}

    def _check_safety(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        lowered = text.lower()
        risk_terms = ["suicide", "self-harm", "kill myself", "end my life", "harm others"]
        hits = [t for t in risk_terms if t in lowered]
        if hits:
            return False, {
                "severity": Severity.CRITICAL.value,
                "evidence": f"Safety risk terms: {hits}",
                "risk_signals": hits,
            }
        return True, {"risk_signals": hits}

    def _check_completeness(self, text: str, context: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        word_count = len(text.split())
        if word_count < 3 and context and len(context.split()) > 10:
            return False, {
                "severity": Severity.INFO.value,
                "evidence": "Very short response for complex query",
                "word_count": word_count,
                "context_word_count": len(context.split()),
            }
        return True, {"word_count": word_count}

    def _compute_score(self, critiques: List[Dict[str, Any]]) -> float:
        if not critiques:
            return 1.0
        penalty = 0.0
        for c in critiques:
            sev = c.get("severity", "warning")
            penalty += {
                "none": 0.0, "info": 0.02, "warning": 0.05, "error": 0.1, "critical": 0.2
            }.get(sev, 0.05)
        return max(0.0, 1.0 - min(penalty, 1.0))

    def _summarize(self, critiques: List[Dict[str, Any]], score: float) -> str:
        if not critiques:
            return f"Passed all checks (score={score:.2f})"
        types = [c["type"] for c in critiques]
        return f"Failed checks: {', '.join(types)} (score={score:.2f})"

    def check_batch(self, texts: List[str], context: Optional[str] = None) -> List[CritiqueResult]:
        return [self.check(text, context=context) for text in texts]

    def validate(self, text: str, context: Optional[str] = None) -> bool:
        return self.check(text, context=context).passed


self_checker = SelfChecker()
