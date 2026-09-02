"""Performance optimization utilities."""

import time
import logging
import functools
import asyncio
from typing import Optional, Any, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class Cache:
    """Simple TTL cache."""

    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                self._hits += 1
                return value
            del self._cache[key]
        self._misses += 1
        return None

    def set(self, key: str, value: Any):
        if len(self._cache) >= self._max_size:
            self._evict()
        self._cache[key] = (value, time.time() + self._ttl)

    def invalidate(self, key: str):
        self._cache.pop(key, None)

    def clear(self):
        self._cache.clear()

    def _evict(self):
        """Remove oldest entries."""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if exp < now]
        for k in expired:
            del self._cache[k]
        if len(self._cache) >= self._max_size:
            oldest = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])[:100]
            for k in oldest:
                del self._cache[k]

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0


class MetricsCollector:
    """Collect and track performance metrics."""

    def __init__(self):
        self._timings: dict[str, list[float]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)

    def record_timing(self, name: str, duration_ms: float):
        self._timings[name].append(duration_ms)
        if len(self._timings[name]) > 1000:
            self._timings[name] = self._timings[name][-500:]

    def increment(self, name: str, count: int = 1):
        self._counters[name] += count

    def get_stats(self, name: str) -> dict:
        timings = self._timings.get(name, [])
        return {
            "count": len(timings),
            "avg_ms": sum(timings) / len(timings) if timings else 0,
            "min_ms": min(timings) if timings else 0,
            "max_ms": max(timings) if timings else 0,
            "p95_ms": sorted(timings)[int(len(timings) * 0.95)] if timings else 0,
        }

    def get_all_stats(self) -> dict:
        return {
            name: self.get_stats(name)
            for name in self._timings
        }


def timed(func: Callable) -> Callable:
    """Decorator to time function execution."""
    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            logger.debug(f"{func.__name__} took {duration:.2f}ms")
            return result
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = (time.perf_counter() - start) * 1000
            logger.debug(f"{func.__name__} took {duration:.2f}ms")
            return result
        return sync_wrapper


# Global instances
cache = Cache()
metrics = MetricsCollector()
