"""Benchmark runner for model evaluation."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    benchmark_id: str
    model_id: str
    suite_name: str
    score: float
    latency_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    executed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BenchmarkSuite:
    suite_id: str
    name: str
    benchmarks: List[Callable[[str], Dict[str, Any]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


class BenchmarkRunner:
    def __init__(self) -> None:
        self._suites: Dict[str, BenchmarkSuite] = {}
        self._results: List[BenchmarkResult] = []

    def register_suite(self, suite: BenchmarkSuite) -> None:
        self._suites[suite.suite_id] = suite

    async def run(self, suite_id: str, model_id: str) -> BenchmarkResult:
        suite = self._suites.get(suite_id)
        if not suite:
            raise ValueError(f"Unknown benchmark suite: {suite_id}")
        start = time.perf_counter()
        scores = []
        for benchmark in suite.benchmarks:
            result = benchmark(model_id)
            scores.append(result.get("score", 0.0))
        latency = (time.perf_counter() - start) * 1000
        avg_score = sum(scores) / len(scores) if scores else 0.0
        bench_result = BenchmarkResult(
            benchmark_id=uuid.uuid4().hex,
            model_id=model_id,
            suite_name=suite.name,
            score=avg_score,
            latency_ms=latency,
        )
        self._results.append(bench_result)
        return bench_result

    def get_results(self, model_id: Optional[str] = None) -> List[BenchmarkResult]:
        if model_id:
            return [r for r in self._results if r.model_id == model_id]
        return list(self._results)


benchmark_runner = BenchmarkRunner()
