import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class InvariantResult:
    name: str
    passed: bool
    context: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class InvariantSuiteResult:
    check_name: str
    runs: int
    passed: int
    failed: int
    duration_ms: float
    failures: List[InvariantResult] = field(default_factory=list)


class InvariantChecker:
    def __init__(self, tolerance: float = 0.0):
        self.tolerance = tolerance
        self._history: List[InvariantSuiteResult] = []

    def check(
        self,
        name: str,
        condition: Callable[[], bool],
        context: Optional[Dict[str, Any]] = None,
    ) -> InvariantResult:
        ctx = context or {}
        start = _perf_counter()
        try:
            holds = bool(condition())
            duration = (_perf_counter() - start) * 1000
            return InvariantResult(
                name=name,
                passed=holds,
                context=ctx,
                duration_ms=duration,
            )
        except Exception as exc:
            duration = (_perf_counter() - start) * 1000
            return InvariantResult(
                name=name,
                passed=False,
                context=ctx,
                error=str(exc),
                duration_ms=duration,
            )

    def run_suite(
        self,
        name: str,
        checks: Dict[str, Callable[[], bool]],
        context: Optional[Dict[str, Any]] = None,
    ) -> InvariantSuiteResult:
        failures: List[InvariantResult] = []
        passed = 0
        failed = 0
        total_duration = 0.0
        for check_name, condition in checks.items():
            result = self.check(check_name, condition, context)
            total_duration += result.duration_ms
            if result.passed:
                passed += 1
            else:
                failed += 1
                failures.append(result)
        suite = InvariantSuiteResult(
            check_name=name,
            runs=len(checks),
            passed=passed,
            failed=failed,
            duration_ms=round(total_duration, 3),
            failures=failures,
        )
        self._history.append(suite)
        return suite

    def summary(self) -> Dict[str, Any]:
        total_runs = sum(s.runs for s in self._history)
        total_passed = sum(s.passed for s in self._history)
        total_failed = sum(s.failed for s in self._history)
        return {
            "suites": len(self._history),
            "runs": total_runs,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": round(total_passed / max(total_runs, 1), 4),
        }


def _perf_counter() -> float:
    import time
    return time.perf_counter()
