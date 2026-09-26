"""Benchmark suite for standardized model evaluation."""
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    name: str
    accuracy: float
    samples: int
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkSuite:
    def __init__(self):
        self._results: List[BenchmarkResult] = []

    def register(self, name: str, samples: int = 100) -> BenchmarkResult:
        return BenchmarkResult(name=name, accuracy=0.0, samples=samples, latency_ms=0.0)

    def evaluate(
        self, benchmark: BenchmarkResult, accuracy: float, latency_ms: float = 0.0
    ) -> BenchmarkResult:
        benchmark.accuracy = accuracy
        benchmark.latency_ms = latency_ms
        self._results.append(benchmark)
        logger.info(
            "Benchmark %s: accuracy=%.4f latency=%dms",
            benchmark.name, accuracy, int(latency_ms),
        )
        return benchmark

    def run_all(self, benchmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        for item in benchmarks:
            start = time.time()
            accuracy = self._run_benchmark(item)
            latency = (time.time() - start) * 1000
            results.append(self.evaluate(item["name"], accuracy, latency))
        return self._summarize(results)

    def _run_benchmark(self, item: Dict[str, Any]) -> float:
        return item.get("accuracy", 0.0)

    def _summarize(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        return {
            "benchmarks": [r.__dict__ for r in results],
            "overall_accuracy": sum(r.accuracy for r in results) / len(results) if results else 0.0,
            "total_samples": sum(r.samples for r in results),
            "mean_latency_ms": (
                sum(r.latency_ms for r in results) / len(results) if results else 0.0
            ),
        }

    def get_results(self) -> List[Dict[str, Any]]:
        return [r.__dict__ for r in self._results]
