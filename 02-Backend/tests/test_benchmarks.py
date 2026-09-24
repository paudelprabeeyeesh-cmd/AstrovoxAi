
import asyncio
import statistics
from unittest.mock import MagicMock

import pytest

from app.benchmark import PerformanceBenchmark


class TestPerformanceBenchmark:
    def test_benchmark_sync_returns_result(self):
        bench = PerformanceBenchmark()
        result = bench.benchmark_sync("sync_op", lambda: 1 + 1, iterations=10)
        assert result.name == "sync_op"
        assert result.iterations == 10
        assert result.avg_time_ms >= 0

    def test_benchmark_sync_stats(self):
        bench = PerformanceBenchmark()
        result = bench.benchmark_sync("sync_stats", lambda: sum(range(100)), iterations=20)
        assert result.median_time_ms >= 0
        assert result.p95_time_ms >= result.median_time_ms
        assert result.p99_time_ms >= result.p95_time_ms
        assert result.min_time_ms <= result.avg_time_ms <= result.max_time_ms
        assert result.ops_per_second > 0

    @pytest.mark.asyncio
    async def test_benchmark_async_returns_result(self):
        bench = PerformanceBenchmark()

        async def async_op():
            return 1 + 1

        result = await bench.benchmark_async("async_op", async_op, iterations=10)
        assert result.name == "async_op"
        assert result.iterations == 10
        assert result.avg_time_ms >= 0

    @pytest.mark.asyncio
    async def test_run_suite_returns_dict(self):
        bench = PerformanceBenchmark()

        async def task_a():
            return "a"

        async def task_b():
            return "b"

        results = await bench.run_suite({"a": task_a, "b": task_b}, iterations=5)
        assert isinstance(results, dict)
        assert "a" in results
        assert "b" in results

    def test_get_summary_empty(self):
        bench = PerformanceBenchmark()
        summary = bench.get_summary()
        assert summary == {}

    def test_get_summary_populated(self):
        bench = PerformanceBenchmark()
        bench.benchmark_sync("op1", lambda: None, iterations=5)
        bench.benchmark_sync("op2", lambda: None, iterations=5)
        summary = bench.get_summary()
        assert summary["suites"] == 2
        assert summary["total_iterations"] == 10
        assert "slowest_suite" in summary
        assert "fastest_suite" in summary
        assert len(summary["results"]) == 2

    def test_benchmark_handles_exception(self):
        bench = PerformanceBenchmark()

        def failing_op():
            raise RuntimeError("boom")

        result = bench.benchmark_sync("failing", failing_op, iterations=5)
        assert result.iterations == 5
        assert result.avg_time_ms >= 0

    def test_benchmark_zero_iterations(self):
        bench = PerformanceBenchmark()
        result = bench.benchmark_sync("zero", lambda: None, iterations=0)
        assert result.iterations == 0
        assert result.ops_per_second == 0

    def test_benchmark_single_iteration(self):
        bench = PerformanceBenchmark()
        result = bench.benchmark_sync("single", lambda: None, iterations=1)
        assert result.iterations == 1
        assert result.avg_time_ms == result.min_time_ms == result.max_time_ms

    def test_multiple_benchmarks_accumulate(self):
        bench = PerformanceBenchmark()
        bench.benchmark_sync("a", lambda: None, iterations=3)
        bench.benchmark_sync("b", lambda: None, iterations=7)
        summary = bench.get_summary()
        assert summary["total_iterations"] == 10
