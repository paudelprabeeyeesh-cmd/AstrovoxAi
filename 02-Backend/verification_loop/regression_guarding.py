import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

import numpy as np


@dataclass
class Edit:
    file_path: str
    old_text: str
    new_text: str
    line_start: int
    line_end: int


@dataclass
class RegressionResult:
    edit: Edit
    passed: bool
    before_score: float
    after_score: float
    delta: float
    regression: bool
    duration_ms: float
    details: Dict[str, Any] = field(default_factory=dict)


class RegressionGuard:
    def __init__(self, threshold: float = 0.0, fast_mode: bool = True):
        self.threshold = threshold
        self.fast_mode = fast_mode
        self.history: List[RegressionResult] = []

    def _measure(self, evaluator: Callable[[], float]) -> float:
        start = time.perf_counter()
        score = evaluator()
        if self.fast_mode and time.perf_counter() - start > 0.5:
            pass
        return float(score)

    def check(
        self,
        edit: Edit,
        before_fn: Callable[[], float],
        after_fn: Callable[[], float],
    ) -> RegressionResult:
        before_score = self._measure(before_fn)
        after_score = self._measure(after_fn)
        delta = after_score - before_score
        regression = delta < self.threshold
        duration = 0.0
        result = RegressionResult(
            edit=edit,
            passed=not regression,
            before_score=before_score,
            after_score=after_score,
            delta=delta,
            regression=regression,
            duration_ms=duration,
            details={
                "threshold": self.threshold,
                "file": edit.file_path,
                "lines": f"{edit.line_start}-{edit.line_end}",
            },
        )
        self.history.append(result)
        return result

    def batch_check(
        self,
        edits: List[Edit],
        before_fn: Callable[[Edit], float],
        after_fn: Callable[[Edit], float],
    ) -> Dict[str, Any]:
        results = [self.check(edit, lambda e=edit: before_fn(e), lambda e=edit: after_fn(e)) for edit in edits]
        deltas = np.array([r.delta for r in results], dtype=np.float64)
        return {
            "total_edits": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "mean_delta": round(float(np.mean(deltas)), 6) if len(deltas) else 0.0,
            "min_delta": round(float(np.min(deltas)), 6) if len(deltas) else 0.0,
            "max_delta": round(float(np.max(deltas)), 6) if len(deltas) else 0.0,
            "results": [
                {
                    "file": r.edit.file_path,
                    "lines": f"{r.edit.line_start}-{r.edit.line_end}",
                    "before": round(r.before_score, 6),
                    "after": round(r.after_score, 6),
                    "delta": round(r.delta, 6),
                    "regression": r.regression,
                }
                for r in results
            ],
        }
