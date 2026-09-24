import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from statistics import mean

logger = logging.getLogger(__name__)


@dataclass
class RegressionRecord:
    name: str
    baseline: float
    current: float
    delta: float
    threshold: float
    is_regression: bool
    metadata: dict = field(default_factory=dict)


class RegressionChecker:
    def __init__(self, default_threshold: float = 0.05):
        self.default_threshold = default_threshold
        self._baselines: Dict[str, float] = {}
        self._history: Dict[str, List[float]] = {}

    def set_baseline(self, name: str, score: float) -> None:
        self._baselines[name] = score

    def get_baseline(self, name: str) -> Optional[float]:
        return self._baselines.get(name)

    def check(self, name: str, current_score: float, threshold: Optional[float] = None) -> RegressionRecord:
        threshold = threshold if threshold is not None else self.default_threshold
        baseline = self._baselines.get(name)

        if baseline is None:
            self._baselines[name] = current_score
            self._history.setdefault(name, []).append(current_score)
            return RegressionRecord(
                name=name,
                baseline=current_score,
                current=current_score,
                delta=0.0,
                threshold=threshold,
                is_regression=False,
            )

        delta = baseline - current_score
        is_regression = delta > threshold

        self._history.setdefault(name, []).append(current_score)

        return RegressionRecord(
            name=name,
            baseline=baseline,
            current=current_score,
            delta=delta,
            threshold=threshold,
            is_regression=is_regression,
        )

    def check_suite(self, results: Dict[str, float], threshold: Optional[float] = None) -> List[RegressionRecord]:
        return [self.check(name, score, threshold) for name, score in results.items()]

    def has_regression(self, results: Dict[str, float], threshold: Optional[float] = None) -> bool:
        return any(r.is_regression for r in self.check_suite(results, threshold))

    def history(self, name: str) -> List[float]:
        return list(self._history.get(name, []))

    def export_report(self) -> Dict[str, Any]:
        return {
            "baselines": dict(self._baselines),
            "history": {k: list(v) for k, v in self._history.items()},
        }
