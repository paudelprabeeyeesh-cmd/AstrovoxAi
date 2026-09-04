"""Tests for the load testing and capacity planning framework."""

from __future__ import annotations

import asyncio
import unittest

from app.load_testing import (
    CapacityPlan,
    LoadGenerator,
    LoadTestConfig,
    LoadTestResult,
    StabilityReport,
    StabilityTest,
    capacity_plan,
)


async def _quick_ok() -> str:
    await asyncio.sleep(0.001)
    return "ok"


async def _slow() -> str:
    await asyncio.sleep(0.1)
    return "slow"


async def _always_fail() -> None:
    raise ValueError("nope")


class LoadGeneratorTest(unittest.TestCase):
    def test_runs_and_collects_metrics(self):
        async def run():
            config = LoadTestConfig(
                name="test",
                target_rps=100,
                duration_s=1.0,
                concurrency=8,
                warmup_s=0.0,
                timeout_s=5.0,
            )
            gen = LoadGenerator(config)
            result = await gen.run(_quick_ok)
            return result

        result = asyncio.run(run())
        self.assertGreater(result.total_requests, 0)
        self.assertEqual(result.failed, 0)
        self.assertGreater(result.throughput_rps, 0)
        self.assertGreater(result.latency.samples, 0)

    def test_detects_failures(self):
        async def run():
            config = LoadTestConfig(
                name="fail-test",
                target_rps=50,
                duration_s=0.5,
                concurrency=4,
                warmup_s=0.0,
                failure_threshold=0.1,
            )
            gen = LoadGenerator(config)
            return await gen.run(_always_fail)

        result = asyncio.run(run())
        self.assertGreater(result.failed, 0)
        self.assertFalse(result.passed)
        self.assertIn("ValueError", result.error_breakdown)

    def test_meets_latency_budget(self):
        async def run():
            config = LoadTestConfig(
                name="latency-test",
                target_rps=50,
                duration_s=0.5,
                concurrency=4,
                warmup_s=0.0,
                latency_p95_budget_ms=500.0,
            )
            gen = LoadGenerator(config)
            return await gen.run(_slow)

        result = asyncio.run(run())
        # _slow has 100ms latency which is under 500ms budget
        self.assertTrue(result.passed, msg=str(result.violations))

    def test_violates_latency_budget(self):
        async def run():
            config = LoadTestConfig(
                name="violating",
                target_rps=50,
                duration_s=0.5,
                concurrency=2,
                warmup_s=0.0,
                latency_p95_budget_ms=10.0,
            )
            gen = LoadGenerator(config)
            return await gen.run(_slow)

        result = asyncio.run(run())
        # _slow has 100ms latency which exceeds 10ms budget
        self.assertFalse(result.passed)


class CapacityPlanningTest(unittest.TestCase):
    def test_basic_plan(self):
        plan = capacity_plan(
            target_rps=1000,
            avg_latency_ms=50,
            p95_latency_ms=120,
        )
        self.assertEqual(plan.target_rps, 1000)
        self.assertGreater(plan.concurrency, 0)
        self.assertGreater(plan.cpu_cores, 0)
        self.assertGreater(plan.required_workers, 0)

    def test_high_rps_needs_more_concurrency(self):
        plan_low = capacity_plan(target_rps=10, avg_latency_ms=100)
        plan_high = capacity_plan(target_rps=1000, avg_latency_ms=100)
        self.assertGreater(plan_high.concurrency, plan_low.concurrency)

    def test_storage_projection(self):
        plan = capacity_plan(target_rps=100, avg_latency_ms=10)
        self.assertGreaterEqual(plan.storage_gb, 0)

    def test_to_dict(self):
        plan = capacity_plan(target_rps=100, avg_latency_ms=10)
        d = plan.to_dict()
        self.assertIn("target_rps", d)
        self.assertIn("required_workers", d)


class StabilityTestTest(unittest.TestCase):
    def test_no_leak_detected(self):
        test = StabilityTest(duration_s=60)
        for i in range(5):
            test.record_sample(memory_mb=100 + i, error_rate=0.01)
        report = test.build_report()
        self.assertFalse(report.memory_leak_detected)

    def test_memory_leak_detected(self):
        test = StabilityTest(duration_s=3600)
        # Simulate memory growth from 100MB to 300MB
        for i in range(10):
            test.record_sample(memory_mb=100 + (i * 25), error_rate=0.01)
        report = test.build_report()
        self.assertTrue(report.memory_leak_detected)

    def test_error_trend_positive(self):
        test = StabilityTest(duration_s=3600)
        for i in range(10):
            # Errors grow from 1% to 10%
            test.record_sample(memory_mb=100, error_rate=0.01 + (i * 0.01))
        report = test.build_report()
        self.assertGreater(report.error_rate_trend, 0)
        self.assertTrue(report.health_degradation)

    def test_to_dict(self):
        test = StabilityTest()
        test.record_sample(memory_mb=100, error_rate=0.01)
        report = test.build_report()
        d = report.to_dict()
        self.assertIn("duration_s", d)
        self.assertIn("memory_leak_detected", d)


if __name__ == "__main__":
    unittest.main()
