"""Benchmark suite for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class BenchmarkResult:
    """A benchmark result."""
    name: str
    value: float
    unit: str = "ms"
    iterations: int = 1000

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "unit": self.unit,
                "iterations": self.iterations}


class BenchmarkSuite:
    """Run microbenchmarks."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []

    def measure(self, fn, iterations: int = 10000, name: str = "unnamed") -> BenchmarkResult:
        start = time.perf_counter()
        for _ in range(iterations):
            fn()
        elapsed = (time.perf_counter() - start) * 1000
        per_iter = elapsed / iterations
        result = BenchmarkResult(name=name, value=per_iter, unit="ms", iterations=iterations)
        self.results.append(result)
        return result

    def measure_async(self, coro_fn, iterations: int = 1000, name: str = "unnamed") -> BenchmarkResult:
        import asyncio
        start = time.perf_counter()
        loop = asyncio.new_event_loop()
        for _ in range(iterations):
            loop.run_until_complete(coro_fn())
        elapsed = (time.perf_counter() - start) * 1000
        per_iter = elapsed / iterations
        result = BenchmarkResult(name=name, value=per_iter, unit="ms", iterations=iterations)
        self.results.append(result)
        return result

    def summary(self) -> list[dict]:
        return [r.to_dict() for r in self.results]

    def best(self) -> BenchmarkResult | None:
        return min(self.results, key=lambda r: r.value) if self.results else None

    def reset(self) -> None:
        self.results.clear()
