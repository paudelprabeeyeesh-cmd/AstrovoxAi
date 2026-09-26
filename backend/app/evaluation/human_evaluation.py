"""Human evaluation tracking and aggregation."""
import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class HumanEvalResult:
    eval_id: str
    rater_id: str
    case_id: str
    score: float
    max_score: float = 5.0
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class HumanEvaluationTracker:
    def __init__(self):
        self._results: List[HumanEvalResult] = []

    def record(
        self, eval_id: str, rater_id: str, case_id: str, score: float, notes: str = ""
    ) -> HumanEvalResult:
        result = HumanEvalResult(
            eval_id=eval_id,
            rater_id=rater_id,
            case_id=case_id,
            score=score,
            notes=notes,
        )
        self._results.append(result)
        logger.info("Human eval %s recorded by %s", eval_id, rater_id)
        return result

    def aggregate_by_case(self, case_id: str) -> Dict[str, Any]:
        case_results = [r for r in self._results if r.case_id == case_id]
        if not case_results:
            return {"case_id": case_id, "count": 0, "mean": 0.0}
        scores = [r.score / r.max_score for r in case_results]
        return {
            "case_id": case_id,
            "count": len(case_results),
            "mean": statistics.mean(scores),
            "stddev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "raters": list({r.rater_id for r in case_results}),
        }

    def rater_reliability(self) -> Dict[str, Dict[str, Any]]:
        reliability: Dict[str, List[float]] = {}
        for r in self._results:
            reliability.setdefault(r.rater_id, []).append(r.score / r.max_score)
        return {
            rater: {
                "count": len(scores),
                "mean": statistics.mean(scores),
                "stddev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            }
            for rater, scores in reliability.items()
        }

    def summary(self) -> Dict[str, Any]:
        if not self._results:
            return {"total": 0, "mean": 0.0}
        scores = [r.score / r.max_score for r in self._results]
        return {
            "total": len(self._results),
            "mean": statistics.mean(scores),
            "stddev": statistics.stdev(scores) if len(scores) > 1 else 0.0,
            "min": min(scores),
            "max": max(scores),
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._results]
