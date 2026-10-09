"""
End-to-end integration testing harness.

Executes integration test scenarios, collects results, and reports outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TestScenario:
    __test__ = False
    name: str
    steps: List[Callable[[], Any]]
    teardowns: List[Callable[[], Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    timeout: float = 30.0


@dataclass
class TestResult:
    __test__ = False
    scenario: str
    passed: bool
    steps_passed: int = 0
    steps_failed: int = 0
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class IntegrationTester:
    def __init__(self) -> None:
        self._scenarios: Dict[str, TestScenario] = {}
        self._results: Dict[str, TestResult] = {}
        self._hook = None
        self._before: Dict[str, Callable] = {}
        self._after: Dict[str, Callable] = {}

    def register(self, scenario: TestScenario) -> None:
        self._scenarios[scenario.name] = scenario

    def set_hook(self, hook: Callable[[str, str], None]) -> None:
        self._hook = hook

    def run_all(self) -> Dict[str, TestResult]:
        results = {}
        for name, scenario in self._scenarios.items():
            before = self._before.get(name)
            if before:
                before()
            results[name] = self._run_scenario(scenario)
            after = self._after.get(name)
            if after:
                after()
        self._results.update(results)
        return results

    def _run_scenario(self, scenario: TestScenario) -> TestResult:
        passed = 0
        failed = 0
        error = None
        for idx, step in enumerate(scenario.steps):
            try:
                step()
                passed += 1
            except AssertionError as exc:
                error = str(exc)
                failed += 1
                break
            except Exception as _e:  # noqa: BLE001
                error = str(_e)
                failed += 1
                break
        for td in scenario.teardowns:
            try:
                td()
            except Exception as _e:  # noqa: BLE001
                continue
        if error:
            return TestResult(scenario=scenario.name, passed=False, steps_passed=passed, steps_failed=failed, error=error)
        return TestResult(scenario=scenario.name, passed=failed == 0, steps_passed=passed, steps_failed=failed)

    def results(self) -> Dict[str, TestResult]:
        return dict(self._results)

    def summary(self) -> Dict[str, Any]:
        total = len(self._results)
        passed = sum(1 for r in self._results.values() if r.passed)
        failed = total - passed
        return {"total": total, "passed": passed, "failed": failed}

    def _before(self, name: str, fn: Callable) -> None:
        self._before[name] = fn

    def _after(self, name: str, fn: Callable) -> None:
        self._after[name] = fn


class E2ERunner:
    def __init__(self, tester: IntegrationTester) -> None:
        self.tester = tester

    def run(self) -> Dict[str, Any]:
        results = self.tester.run_all()
        return {"results": {k: r.__dict__ for k, r in results.items()}, "summary": self.tester.summary()}
