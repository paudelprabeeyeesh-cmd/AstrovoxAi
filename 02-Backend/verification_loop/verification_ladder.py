from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


class LadderStage(Enum):
    SYNTAX = "syntax"
    TYPE = "type"
    LINT = "lint"
    BUILD = "build"
    TARGETED_TESTS = "targeted_tests"
    FULL_SUITE = "full_suite"


@dataclass
class StageResult:
    stage: LadderStage
    passed: bool
    duration_ms: float
    error_count: int
    details: Dict[str, Any] = field(default_factory=dict)


class VerificationLadder:
    def __init__(self, stop_on_failure: bool = True):
        self.stop_on_failure = stop_on_failure
        self.results: List[StageResult] = []

    def _run_stage(
        self,
        stage: LadderStage,
        checker: Callable[[], Dict[str, Any]],
    ) -> StageResult:
        start = __import__("time").perf_counter()
        try:
            details = checker()
            passed = details.get("passed", True)
            error_count = details.get("error_count", 0)
        except Exception as exc:
            passed = False
            error_count = 1
            details = {"exception": str(exc)}
        duration = (__import__("time").perf_counter() - start) * 1000
        return StageResult(
            stage=stage,
            passed=passed,
            duration_ms=duration,
            error_count=error_count,
            details=details,
        )

    def run(
        self,
        checks: Dict[LadderStage, Callable[[], Dict[str, Any]]],
    ) -> Dict[str, Any]:
        self.results = []
        ordered = [s for s in LadderStage if s in checks]
        for stage in ordered:
            result = self._run_stage(stage, checks[stage])
            self.results.append(result)
            if self.stop_on_failure and not result.passed:
                break
        passed = sum(1 for r in self.results if r.passed)
        durations = np.array([r.duration_ms for r in self.results], dtype=np.float64)
        return {
            "stages_run": len(self.results),
            "stages_passed": passed,
            "stages_failed": len(self.results) - passed,
            "total_duration_ms": float(np.sum(durations)),
            "mean_duration_ms": float(np.mean(durations)) if len(durations) else 0.0,
            "p95_duration_ms": float(np.percentile(durations, 95)) if len(durations) else 0.0,
            "results": [
                {
                    "stage": r.stage.value,
                    "passed": r.passed,
                    "duration_ms": round(r.duration_ms, 3),
                    "error_count": r.error_count,
                    "details": r.details,
                }
                for r in self.results
            ],
        }
