"""Accuracy scoring across QA, summarization, and reasoning tasks."""
import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class AccuracyResult:
    task_type: str
    case_id: str
    correct: bool
    score: float
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class AccuracyScorer:
    def __init__(self):
        self._results: List[AccuracyResult] = []

    def score_exact(
        self, task_type: str, case_id: str, prediction: str, reference: str, latency_ms: float = 0.0
    ) -> AccuracyResult:
        correct = prediction.strip().lower() == reference.strip().lower()
        return AccuracyResult(
            task_type=task_type,
            case_id=case_id,
            correct=correct,
            score=1.0 if correct else 0.0,
            latency_ms=latency_ms,
        )

    def score_fuzzy(self, task_type: str, case_id: str, prediction: str, reference: str, latency_ms: float = 0.0) -> AccuracyResult:
        pred_tokens = set(prediction.lower().split())
        ref_tokens = set(reference.lower().split())
        if not ref_tokens:
            score = 1.0
        else:
            intersection = pred_tokens & ref_tokens
            score = len(intersection) / len(ref_tokens)
        correct = score >= 0.8
        return AccuracyResult(
            task_type=task_type,
            case_id=case_id,
            correct=correct,
            score=score,
            latency_ms=latency_ms,
            metadata={"method": "fuzzy"},
        )

    def run_suite(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in cases:
            mode = case.get("mode", "exact")
            if mode == "fuzzy":
                result = self.score_fuzzy(case["task_type"], case["case_id"], case["prediction"], case["reference"])
            else:
                result = self.score_exact(case["task_type"], case["case_id"], case["prediction"], case["reference"])
            self._results.append(result)
            results.append(result)
        return self._summarize(results)

    def _summarize(self, results: List[AccuracyResult]) -> Dict[str, Any]:
        by_task: Dict[str, List[float]] = {}
        for r in results:
            by_task.setdefault(r.task_type, []).append(r.score)
        return {
            "total": len(results),
            "overall_accuracy": statistics.mean([r.score for r in results]) if results else 0.0,
            "exact_match_rate": sum(1 for r in results if r.correct) / len(results) if results else 0.0,
            "by_task": {task: statistics.mean(scores) for task, scores in by_task.items()},
            "mean_latency_ms": statistics.mean([r.latency_ms for r in results]) if results else 0.0,
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._results]
