from __future__ import annotations

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    name: str
    runner: Any
    iterations: int = 3


@dataclass
class BenchmarkResult:
    case_id: str
    name: str
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput: float
    errors: int


class BenchmarkPlatform:
    def __init__(self):
        self._cases: dict[str, BenchmarkCase] = {}

    def register(self, name: str, runner, iterations: int = 3) -> BenchmarkCase:
        case_id = str(uuid.uuid4())
        case = BenchmarkCase(id=case_id, name=name, runner=runner, iterations=iterations)
        self._cases[case_id] = case
        return case

    def run(self, case_id: str) -> BenchmarkResult:
        case = self._cases.get(case_id)
        if not case:
            raise ValueError(f"Benchmark {case_id} not found")
        latencies = []
        errors = 0
        for _ in range(case.iterations):
            start = time.perf_counter()
            try:
                case.runner()
                latencies.append((time.perf_counter() - start) * 1000)
            except Exception as exc:
                errors += 1
                logger.error("Benchmark %s iteration failed: %s", case.name, exc)
        if not latencies:
            latencies = [0.0]
        return BenchmarkResult(
            case_id=case.id,
            name=case.name,
            avg_latency_ms=sum(latencies) / len(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            throughput=1000 / (sum(latencies) / len(latencies)) if latencies else 0.0,
            errors=errors,
        )

    def run_all(self) -> list[BenchmarkResult]:
        return [self.run(cid) for cid in self._cases]

    def compare(self, case_ids: list[str]) -> dict[str, BenchmarkResult]:
        return {cid: self.run(cid) for cid in case_ids if cid in self._cases}


benchmark_platform = BenchmarkPlatform()
class BenchmarkSuiteResult:
    name: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    median_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    min_time_ms: float
    max_time_ms: float
    std_dev_ms: float
    ops_per_second: float


class PerformanceBenchmark:
    """Runs performance benchmarks on backend operations."""

    def __init__(self):
        self._results: List[BenchmarkSuiteResult] = []

    def benchmark_sync(self, name: str, func: Callable[[], Any], iterations: int = 100) -> BenchmarkSuiteResult:
        times: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                func()
            except Exception as exc:  # noqa: BLE001
                logger.error("Benchmark %s iteration failed: %s", name, exc)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        times.sort()
        result = self._compute_stats(name, iterations, times)
        self._results.append(result)
        return result

    async def benchmark_async(self, name: str, func: Callable[[], Coroutine], iterations: int = 100) -> BenchmarkSuiteResult:
        times: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            try:
                await func()
            except Exception as exc:  # noqa: BLE001
                logger.error("Benchmark %s iteration failed: %s", name, exc)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        times.sort()
        result = self._compute_stats(name, iterations, times)
        self._results.append(result)
        return result

    def _compute_stats(self, name: str, iterations: int, times: List[float]) -> BenchmarkSuiteResult:
        total = sum(times)
        p95_idx = int(iterations * 0.95)
        p99_idx = int(iterations * 0.99)
        return BenchmarkSuiteResult(
            name=name,
            iterations=iterations,
            total_time_ms=total,
            avg_time_ms=statistics.mean(times),
            median_time_ms=statistics.median(times),
            p95_time_ms=times[min(p95_idx, len(times) - 1)],
            p99_time_ms=times[min(p99_idx, len(times) - 1)],
            min_time_ms=times[0],
            max_time_ms=times[-1],
            std_dev_ms=statistics.pstdev(times),
            ops_per_second=iterations / (total / 1000.0) if total else 0,
        )

    async def run_suite(self, tests: Dict[str, Callable[[], Coroutine]], iterations: int = 50) -> Dict[str, BenchmarkSuiteResult]:
        results = {}
        for name, func in tests.items():
            results[name] = await self.benchmark_async(name, func, iterations)
        return results

    def get_summary(self) -> Dict[str, Any]:
        if not self._results:
            return {}
        return {
            "suites": len(self._results),
            "total_iterations": sum(r.iterations for r in self._results),
            "slowest_suite": max(self._results, key=lambda r: r.avg_time_ms).name,
            "fastest_suite": min(self._results, key=lambda r: r.avg_time_ms).name,
            "results": [
                {
                    "name": r.name,
                    "avg_ms": round(r.avg_time_ms, 3),
                    "p95_ms": round(r.p95_time_ms, 3),
                    "p99_ms": round(r.p99_time_ms, 3),
                    "ops_per_second": round(r.ops_per_second, 2),
                }
                for r in self._results
            ],
        }


benchmark = PerformanceBenchmark()
