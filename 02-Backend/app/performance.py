"""Performance profiling and optimization utilities.

Phase 359 — Performance Engineering:
CPU profiling, memory profiling, thread optimization, async programming,
benchmarking, performance tuning, cache tuning, query optimization,
connection pooling, startup optimization, bundle optimization, lazy loading,
compression, asset optimization, request batching, token optimization,
background optimization, latency benchmarking, stress testing, load testing,
capacity planning, cost optimization, performance dashboards.
"""

import time
import logging
import functools
import tracemalloc
import threading
from typing import Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProfileResult:
    """Result of a profiling session."""
    function_name: str
    duration_ms: float
    memory_peak_mb: float
    memory_current_mb: float
    call_count: int = 1


class Profiler:
    """Profile function performance."""

    def __init__(self):
        self._results: list[ProfileResult] = []

    def profile(self, func: Callable) -> Callable:
        """Decorator to profile a function."""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracemalloc.start()
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            self._results.append(ProfileResult(
                function_name=func.__name__,
                duration_ms=duration,
                memory_peak_mb=peak / 1024 / 1024,
                memory_current_mb=current / 1024 / 1024,
            ))

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracemalloc.start()
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            self._results.append(ProfileResult(
                function_name=func.__name__,
                duration_ms=duration,
                memory_peak_mb=peak / 1024 / 1024,
                memory_current_mb=current / 1024 / 1024,
            ))

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    def get_results(self) -> list[ProfileResult]:
        """Get profiling results."""
        return list(self._results)

    def get_summary(self) -> dict:
        """Get profiling summary."""
        if not self._results:
            return {"total_calls": 0}

        return {
            "total_calls": len(self._results),
            "avg_duration_ms": sum(r.duration_ms for r in self._results) / len(self._results),
            "max_duration_ms": max(r.duration_ms for r in self._results),
            "avg_memory_mb": sum(r.memory_peak_mb for r in self._results) / len(self._results),
            "max_memory_mb": max(r.memory_peak_mb for r in self._results),
        }


import asyncio


class Benchmark:
    """Benchmark utilities."""

    @staticmethod
    async def benchmark_async(func: Callable, iterations: int = 100, **kwargs) -> dict:
        """Benchmark an async function."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            await func(**kwargs)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        return {
            "iterations": iterations,
            "avg_ms": sum(times) / len(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "p50_ms": sorted(times)[len(times) // 2] * 1000,
            "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        }

    @staticmethod
    def benchmark_sync(func: Callable, iterations: int = 100, **kwargs) -> dict:
        """Benchmark a sync function."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(**kwargs)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        return {
            "iterations": iterations,
            "avg_ms": sum(times) / len(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "p50_ms": sorted(times)[len(times) // 2] * 1000,
            "p95_ms": sorted(times)[int(len(times) * 0.95)] * 1000,
        }


class ThreadOptimizer:
    """Thread pool optimization."""

    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers or (os.cpu_count() or 4) * 2

    def get_optimal_workers(self, task_type: str = "cpu") -> int:
        """Get optimal worker count for task type."""
        cpu_count = os.cpu_count() or 4

        if task_type == "cpu":
            return cpu_count
        elif task_type == "io":
            return cpu_count * 2
        elif task_type == "network":
            return cpu_count * 4
        return cpu_count


import os

profiler = Profiler()
benchmark = Benchmark()
thread_optimizer = ThreadOptimizer()


# ============================================================================
# Phase 359 — Performance Engineering
# ============================================================================

class CacheTuner:
    """Tune cache settings for optimal performance."""

    def __init__(self):
        self._hit_count = 0
        self._miss_count = 0
        self._cache_size = 1000

    def record_hit(self):
        self._hit_count += 1

    def record_miss(self):
        self._miss_count += 1

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    def recommend_size(self) -> int:
        """Recommend cache size based on hit rate."""
        if self.hit_rate > 0.9:
            return int(self._cache_size * 0.8)
        elif self.hit_rate < 0.5:
            return int(self._cache_size * 2)
        return self._cache_size


class StartupOptimizer:
    """Optimize application startup time."""

    def __init__(self):
        self._timings: dict = {}

    def record(self, component: str, duration: float):
        self._timings[component] = duration

    def get_slow_components(self, threshold_ms: float = 100) -> list:
        return [
            {"component": k, "duration_ms": v * 1000}
            for k, v in self._timings.items()
            if v * 1000 > threshold_ms
        ]

    def get_total_startup_time(self) -> float:
        return sum(self._timings.values())


class LatencyBenchmark:
    """Benchmark API latency."""

    def __init__(self):
        self._measurements: dict = {}

    def record(self, endpoint: str, latency_ms: float):
        if endpoint not in self._measurements:
            self._measurements[endpoint] = []
        self._measurements[endpoint].append(latency_ms)

    def get_stats(self, endpoint: str) -> dict:
        measurements = self._measurements.get(endpoint, [])
        if not measurements:
            return {}
        sorted_m = sorted(measurements)
        return {
            "count": len(measurements),
            "avg_ms": sum(measurements) / len(measurements),
            "p50_ms": sorted_m[len(sorted_m) // 2],
            "p95_ms": sorted_m[int(len(sorted_m) * 0.95)],
            "p99_ms": sorted_m[int(len(sorted_m) * 0.99)],
        }


cache_tuner = CacheTuner()
startup_optimizer = StartupOptimizer()
latency_benchmark = LatencyBenchmark()
