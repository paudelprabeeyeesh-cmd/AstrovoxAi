"""Tests for the performance lab."""

from __future__ import annotations

import asyncio
import time
import unittest

from app.executor.performance import (
    Batcher,
    Cache,
    LoadTester,
    Profiler,
    get_cache,
    get_profiler,
)


class ProfilerTest(unittest.TestCase):
    def test_measure_context(self):
        profiler = Profiler()
        with profiler.measure("op"):
            time.sleep(0.001)
        samples = profiler.samples("op")
        self.assertEqual(len(samples), 1)
        self.assertGreater(samples[0].duration_ms, 0)

    def test_manual_start_end(self):
        profiler = Profiler()
        token = profiler.start("manual")
        time.sleep(0.001)
        sample = profiler.end(token, "manual")
        self.assertGreater(sample.duration_ms, 0)

    def test_summary(self):
        profiler = Profiler()
        for _ in range(5):
            with profiler.measure("a"):
                pass
        summary = profiler.summary()
        self.assertIn("a", summary)
        self.assertEqual(summary["a"]["count"], 5)


class CacheTest(unittest.TestCase):
    def test_set_get(self):
        cache = Cache(capacity=10, default_ttl_s=60)
        cache.set("k", "v")
        self.assertEqual(cache.get("k"), "v")

    def test_miss(self):
        cache = Cache()
        self.assertIsNone(cache.get("missing"))

    def test_ttl(self):
        cache = Cache(default_ttl_s=0.0)
        cache.set("k", "v")
        time.sleep(0.01)
        self.assertIsNone(cache.get("k"))

    def test_lru_eviction(self):
        cache = Cache(capacity=2, default_ttl_s=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), 2)
        self.assertEqual(cache.get("c"), 3)


class BatcherTest(unittest.TestCase):
    def test_size_trigger(self):
        flushed = []

        async def flush(items):
            flushed.append(list(items))

        async def run():
            batcher = Batcher(flush, max_size=3, max_wait_ms=10)
            await batcher.submit("a")
            await batcher.submit("b")
            await batcher.submit("c")

        asyncio.run(run())
        self.assertEqual(len(flushed), 1)
        self.assertEqual(flushed[0], ["a", "b", "c"])

    def test_explicit_flush(self):
        flushed = []

        async def flush(items):
            flushed.append(list(items))

        async def run():
            batcher = Batcher(flush, max_size=100, max_wait_ms=1000)
            await batcher.submit("a")
            await batcher.flush()

        asyncio.run(run())
        self.assertEqual(flushed[0], ["a"])


class LoadTesterTest(unittest.TestCase):
    def test_run(self):
        async def target():
            await asyncio.sleep(0.001)
            return "ok"

        tester = LoadTester()
        report = asyncio.run(tester.run(target, iterations=20, concurrency=4))
        self.assertEqual(report["iterations"], 20)
        self.assertGreater(report["avg_ms"], 0)


if __name__ == "__main__":
    unittest.main()