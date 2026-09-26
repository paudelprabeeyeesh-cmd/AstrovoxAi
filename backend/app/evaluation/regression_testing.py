"""Regression testing for model version comparisons."""
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class RegressionResult:
    case_id: str
    passed: bool
    baseline_score: float
    current_score: float
    delta: float
    latency_ms: float
    threshold: float = 0.05
    details: Dict[str, Any] = field(default_factory=dict)


class RegressionTestRunner:
    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold
        self._results: List[RegressionResult] = []

    def register_baseline(self, case_id: str, score: float) -> None:
        self._results.append(RegressionResult(
            case_id=case_id,
            passed=True,
            baseline_score=score,
            current_score=score,
            delta=0.0,
            latency_ms=0.0,
        ))

    def evaluate(
        self, case_id: str, current_score: float, latency_ms: float = 0.0
    ) -> RegressionResult:
        baseline = next((r for r in self._results if r.case_id == case_id), None)
        if baseline is None:
            result = RegressionResult(
                case_id=case_id,
                passed=True,
                baseline_score=current_score,
                current_score=current_score,
                delta=0.0,
                latency_ms=latency_ms,
            )
            self._results.append(result)
            return result

        delta = current_score - baseline.baseline_score
        passed = abs(delta) <= self.threshold
        result = RegressionResult(
            case_id=case_id,
            passed=passed,
            baseline_score=baseline.baseline_score,
            current_score=current_score,
            delta=delta,
            latency_ms=latency_ms,
            threshold=self.threshold,
        )
        baseline.passed = passed
        baseline.current_score = current_score
        baseline.delta = delta
        baseline.latency_ms = latency_ms
        logger.info("Regression %s: delta=%.4f passed=%s", case_id, delta, passed)
        return result

    def run_suite(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for case in cases:
            start = time.time()
            score = self._score_case(case)
            latency = (time.time() - start) * 1000
            results.append(self.evaluate(case["case_id"], score, latency))
        return self._summarize(results)

    def _score_case(self, case: Dict[str, Any]) -> float:
        prompt = case.get("prompt", "")
        expected = case.get("expected", "")
        if not expected:
            return 1.0
        return 0.0 if prompt.strip() != expected.strip() else 1.0

    def _summarize(self, results: List[RegressionResult]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        deltas = [r.delta for r in results]
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total else 0.0,
            "mean_delta": statistics.mean(deltas) if deltas else 0.0,
            "median_delta": statistics.median(deltas) if deltas else 0.0,
            "max_regression": min(deltas) if deltas else 0.0,
            "mean_latency_ms": statistics.mean([r.latency_ms for r in results]) if results else 0.0,
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._results]
