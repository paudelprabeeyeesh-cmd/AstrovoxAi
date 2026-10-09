import logging
import time
from typing import Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    score: float
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RegressionRecord:
    benchmark_name: str
    baseline_score: float
    current_score: float
    delta: float
    threshold: float
    is_regression: bool
    timestamp: float = field(default_factory=time.time)


class RegressionSuite:
    def __init__(self, name: str, threshold: float = 0.05):
        self.name = name
        self.threshold = threshold
        self._history: list[BenchmarkResult] = []
        self._baselines: dict[str, float] = {}

    def add_result(self, result: BenchmarkResult) -> None:
        self._history.append(result)

    def set_baseline(self, benchmark_name: str, score: float) -> None:
        self._baselines[benchmark_name] = score

    def get_baseline(self, benchmark_name: str) -> float | None:
        return self._baselines.get(benchmark_name)

    def check_regression(self, benchmark_name: str, current_score: float) -> RegressionRecord:
        baseline = self._baselines.get(benchmark_name)
        if baseline is None:
            self._baselines[benchmark_name] = current_score
            return RegressionRecord(
                benchmark_name=benchmark_name,
                baseline_score=current_score,
                current_score=current_score,
                delta=0.0,
                threshold=self.threshold,
                is_regression=False,
            )
        delta = baseline - current_score
        is_regression = delta > self.threshold
        return RegressionRecord(
            benchmark_name=benchmark_name,
            baseline_score=baseline,
            current_score=current_score,
            delta=delta,
            threshold=self.threshold,
            is_regression=is_regression,
        )

    def run_suite(self, benchmarks: dict[str, float]) -> list[RegressionRecord]:
        records = []
        for name, score in benchmarks.items():
            records.append(self.check_regression(name, score))
        return records

    def has_regression(self, benchmarks: dict[str, float]) -> bool:
        return any(r.is_regression for r in self.run_suite(benchmarks))

    def get_history(self, benchmark_name: str) -> list[BenchmarkResult]:
        return [r for r in self._history if r.name == benchmark_name]

    def export_report(self) -> dict[str, Any]:
        return {
            "suite": self.name,
            "threshold": self.threshold,
            "baselines": self._baselines,
            "history_count": len(self._history),
        }


class BenchmarkRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._suites: dict[str, RegressionSuite] = {}
        return cls._instance

    def register_suite(self, name: str, threshold: float = 0.05) -> RegressionSuite:
        suite = RegressionSuite(name=name, threshold=threshold)
        self._suites[name] = suite
        return suite

    def get_suite(self, name: str) -> RegressionSuite | None:
        return self._suites.get(name)

    def list_suites(self) -> list[str]:
        return list(self._suites.keys())

    def evaluate_all(self, results: dict[str, dict[str, float]]) -> dict[str, list[RegressionRecord]]:
        all_records = {}
        for suite_name, benchmarks in results.items():
            suite = self.get_suite(suite_name)
            if suite:
                all_records[suite_name] = suite.run_suite(benchmarks)
        return all_records
