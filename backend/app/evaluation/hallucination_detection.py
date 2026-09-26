"""Hallucination detection by comparing outputs to source context."""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class HallucinationResult:
    case_id: str
    hallucinated: bool
    unsupported_claims: int
    supported_claims: int
    score: float
    evidence: Dict[str, Any] = field(default_factory=dict)


class HallucinationDetector:
    def __init__(self):
        self._results: List[HallucinationResult] = []

    def detect(
        self, case_id: str, output: str, context: str, threshold: float = 0.5
    ) -> HallucinationResult:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", output) if s.strip()]
        supported = 0
        unsupported = 0
        evidence = {}
        for idx, sentence in enumerate(sentences):
            claim = sentence.lower()
            tokens = [t for t in re.findall(r"\w+", claim) if len(t) > 3]
            matched = sum(1 for token in tokens if token in context.lower())
            ratio = matched / len(tokens) if tokens else 0.0
            evidence[f"claim_{idx}"] = {
                "text": sentence,
                "support_ratio": ratio,
                "supported": ratio >= threshold,
            }
            if ratio >= threshold:
                supported += 1
            else:
                unsupported += 1
        total = supported + unsupported
        score = supported / total if total else 1.0
        hallucinated = unsupported > supported
        result = HallucinationResult(
            case_id=case_id,
            hallucinated=hallucinated,
            unsupported_claims=unsupported,
            supported_claims=supported,
            score=score,
            evidence=evidence,
        )
        self._results.append(result)
        logger.info("Hallucination %s: score=%.4f unsupported=%d", case_id, score, unsupported)
        return result

    def run_suite(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in cases:
            results.append(self.detect(
                case["case_id"],
                case.get("output", ""),
                case.get("context", ""),
            ))
        return self._summarize(results)

    def _summarize(self, results: List[HallucinationResult]) -> Dict[str, Any]:
        total = len(results)
        hallucinated = sum(1 for r in results if r.hallucinated)
        return {
            "total": total,
            "hallucinated": hallucinated,
            "grounded": total - hallucinated,
            "grounded_rate": (total - hallucinated) / total if total else 0.0,
            "mean_score": sum(r.score for r in results) / total if total else 0.0,
            "mean_unsupported": (
                sum(r.unsupported_claims for r in results) / total if total else 0.0
            ),
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._results]
