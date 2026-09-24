import time
import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from statistics import mean, median, stdev

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkTask:
    name: str
    func: Callable[[], Any]
    metadata: dict = field(default_factory=dict)
    repeats: int = 1


@dataclass
class BenchmarkResult:
    name: str
    times: list[float] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def mean(self) -> float:
        return mean(self.times) if self.times else 0.0

    @property
    def median(self) -> float:
        return median(self.times) if self.times else 0.0

    @property
    def stddev(self) -> float:
        return stdev(self.times) if len(self.times) > 1 else 0.0

    @property
    def min(self) -> float:
        return min(self.times) if self.times else 0.0

    @property
    def max(self) -> float:
        return max(self.times) if self.times else 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "times": list(self.times),
            "mean": self.mean,
            "median": self.median,
            "stddev": self.stddev,
            "min": self.min,
            "max": self.max,
            "metadata": dict(self.metadata),
        }


class BenchmarkRunner:
    def __init__(self):
        self._tasks: Dict[str, BenchmarkTask] = {}
        self._results: Dict[str, BenchmarkResult] = {}

    def register(self, task: BenchmarkTask) -> None:
        self._tasks[task.name] = task

    def run(self, name: Optional[str] = None) -> Dict[str, BenchmarkResult]:
        tasks = self._tasks
        if name is not None:
            tasks = {k: v for k, v in self._tasks.items() if k == name}

        for task_name, task in tasks.items():
            times = []
            for _ in range(task.repeats):
                start = time.perf_counter()
                task.func()
                elapsed = time.perf_counter() - start
                times.append(elapsed)
            result = BenchmarkResult(name=task_name, times=times, metadata=task.metadata)
            self._results[task_name] = result
            logger.info("Benchmark %s completed: mean=%.6fs", task_name, result.mean)

        return self._results

    def get_result(self, name: str) -> Optional[BenchmarkResult]:
        return self._results.get(name)

    def results(self) -> Dict[str, BenchmarkResult]:
        return dict(self._results)
