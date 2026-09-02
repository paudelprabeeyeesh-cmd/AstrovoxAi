"""Tests for performance utilities."""

import pytest
import time
from app.performance import Cache, MetricsCollector, timed


class TestCache:
    def test_set_and_get(self):
        cache = Cache(ttl_seconds=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss(self):
        cache = Cache(ttl_seconds=60)
        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        cache = Cache(ttl_seconds=0)
        cache.set("key1", "value1")
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_cache_invalidate(self):
        cache = Cache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.invalidate("key1")
        assert cache.get("key1") is None

    def test_cache_clear(self):
        cache = Cache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_hit_rate(self):
        cache = Cache(ttl_seconds=60)
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        assert cache.hit_rate == 0.5


class TestMetricsCollector:
    def test_record_timing(self):
        mc = MetricsCollector()
        mc.record_timing("test", 100.0)
        mc.record_timing("test", 200.0)
        stats = mc.get_stats("test")
        assert stats["count"] == 2
        assert stats["avg_ms"] == 150.0

    def test_increment(self):
        mc = MetricsCollector()
        mc.increment("counter")
        mc.increment("counter", 5)
        assert mc._counters["counter"] == 6

    def test_get_all_stats(self):
        mc = MetricsCollector()
        mc.record_timing("op1", 100.0)
        mc.record_timing("op2", 200.0)
        all_stats = mc.get_all_stats()
        assert "op1" in all_stats
        assert "op2" in all_stats


class TestTimedDecorator:
    @pytest.mark.asyncio
    async def test_async_timed(self):
        @timed
        async def slow_func():
            await asyncio.sleep(0.01)
            return "done"

        result = await slow_func()
        assert result == "done"

    def test_sync_timed(self):
        @timed
        def fast_func():
            return "done"

        result = fast_func()
        assert result == "done"
