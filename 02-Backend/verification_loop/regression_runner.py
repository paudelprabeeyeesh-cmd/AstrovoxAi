import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class RegressionRunResult:
    test_name: str
    passed: bool
    baseline: float
    current: float
    delta: float
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RegressionSuiteResult:
    suite_name: str
    total: int
    passed: int
    failed: int
    duration_ms: float
    results: List[RegressionRunResult] = field(default_factory=list)


class RegressionRunner:
    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def run_test(
        self,
        name: str,
        baseline_fn: Callable[[], float],
        current_fn: Callable[[], float],
        details: Optional[Dict[str, Any]] = None,
    ) -> RegressionRunResult:
        start = _perf_counter()
        baseline = float(baseline_fn())
        current = float(current_fn())
        duration = (_perf_counter() - start) * 1000
        delta = current - baseline
        passed = delta >= self.threshold
        return RegressionRunResult(
            test_name=name,
            passed=passed,
            baseline=round(baseline, 6),
            current=round(current, 6),
            delta=round(delta, 6),
            duration_ms=round(duration, 3),
            details=details or {},
        )

    def run_suite(
        self,
        name: str,
        tests: Dict[str, Dict[str, Any]],
    ) -> RegressionSuiteResult:
        results: List[RegressionRunResult] = []
        total_duration = 0.0
        for test_name, spec in tests.items():
            baseline_fn = spec["baseline"]
            current_fn = spec["current"]
            details = spec.get("details", {})
            result = self.run_test(test_name, baseline_fn, current_fn, details)
            total_duration += result.duration_ms
            results.append(result)
        passed = sum(1 for r in results if r.passed)
        return RegressionSuiteResult(
            suite_name=name,
            total=len(results),
            passed=passed,
            failed=len(results) - passed,
            duration_ms=round(total_duration, 3),
            results=results,
        )

    def summarize(self, suite: RegressionSuiteResult) -> Dict[str, Any]:
        deltas = [r.delta for r in suite.results]
        return {
            "suite": suite.suite_name,
            "total": suite.total,
            "passed": suite.passed,
            "failed": suite.failed,
            "pass_rate": round(suite.passed / max(suite.total, 1), 4),
            "mean_delta": round(statistics.mean(deltas), 6) if deltas else 0.0,
            "min_delta": round(min(deltas), 6) if deltas else 0.0,
            "max_delta": round(max(deltas), 6) if deltas else 0.0,
            "duration_ms": suite.duration_ms,
        }


def _perf_counter() -> float:
    import time
    return time.perf_counter()
