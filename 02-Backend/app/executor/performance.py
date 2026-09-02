"""Performance Lab: profiling, batching, caching, and load testing primitives."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, List, Optional, Tuple

from . import make_id, now
from ..logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Profiler
# ---------------------------------------------------------------------------


@dataclass
class ProfileSample:
    name: str
    duration_ms: float
    timestamp: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 4),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class Profiler:
    def __init__(self, history: int = 5000) -> None:
        self._samples: Deque[ProfileSample] = deque(maxlen=history)
        self._active: Dict[str, float] = {}

    def start(self, name: str) -> str:
        token = make_id("prof")
        self._active[token] = time.time()
        return token

    def end(self, token: str, name: Optional[str] = None, **metadata: Any) -> ProfileSample:
        start = self._active.pop(token, None)
        if start is None:
            start = time.time()
        sample = ProfileSample(
            name=name or token,
            duration_ms=(time.time() - start) * 1000,
            metadata=dict(metadata),
        )
        self._samples.append(sample)
        return sample

    def measure(self, name: str) -> "_MeasureContext":
        return _MeasureContext(self, name)

    def samples(self, name: Optional[str] = None, limit: int = 100) -> List[ProfileSample]:
        items = [s for s in self._samples if name is None or s.name == name]
        return list(items)[-limit:]

    def summary(self) -> Dict[str, Any]:
        per_name: Dict[str, List[float]] = {}
        for sample in self._samples:
            per_name.setdefault(sample.name, []).append(sample.duration_ms)
        stats: Dict[str, Any] = {}
        for name, durations in per_name.items():
            sorted_d = sorted(durations)
            n = len(sorted_d)
            stats[name] = {
                "count": n,
                "avg_ms": round(sum(sorted_d) / n, 4),
                "p50_ms": round(sorted_d[n // 2], 4),
                "p95_ms": round(sorted_d[min(n - 1, int(n * 0.95))], 4),
                "max_ms": round(max(sorted_d), 4),
            }
        return stats


class _MeasureContext:
    def __init__(self, profiler: Profiler, name: str) -> None:
        self.profiler = profiler
        self.name = name
        self.token: Optional[str] = None

    def __enter__(self) -> "_MeasureContext":
        self.token = self.profiler.start(self.name)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.token:
            self.profiler.end(self.token, self.name, error=exc_type.__name__ if exc_type else None)


# ---------------------------------------------------------------------------
# Cache with TTL and LRU
# ---------------------------------------------------------------------------


class Cache:
    def __init__(self, capacity: int = 1000, default_ttl_s: float = 60.0) -> None:
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._order: Deque[str] = deque()
        self._capacity = capacity
        self._default_ttl = default_ttl_s
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        expires_at, value = entry
        if expires_at > 0 and expires_at < time.time():
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return value

    def set(self, key: str, value: Any, ttl_s: Optional[float] = None) -> None:
        ttl = ttl_s if ttl_s is not None else self._default_ttl
        # If ttl is zero or negative, the entry is immediately expired.
        if ttl > 0:
            expires_at = time.time() + ttl
        else:
            expires_at = time.time() - 1
        self._store[key] = (expires_at, value)
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)
        if len(self._order) > self._capacity:
            evict = self._order.popleft()
            self._store.pop(evict, None)

    def invalidate(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def stats(self) -> Dict[str, Any]:
        return {
            "size": len(self._store),
            "capacity": self._capacity,
            "hits": self.hits,
            "misses": self.misses,
        }


# ---------------------------------------------------------------------------
# Batcher
# ---------------------------------------------------------------------------


class Batcher:
    """Collects items and flushes them as a batch when size or time threshold is met."""

    def __init__(
        self,
        flush_fn: Callable[[List[Any]], Awaitable[Any]],
        *,
        max_size: int = 16,
        max_wait_ms: float = 50.0,
    ) -> None:
        self._flush = flush_fn
        self._max_size = max_size
        self._max_wait = max_wait_ms / 1000.0
        self._queue: Deque[Any] = deque()
        self._lock = asyncio.Lock()
        self._last_flush = time.time()

    async def submit(self, item: Any) -> Any:
        async with self._lock:
            self._queue.append(item)
            if len(self._queue) >= self._max_size:
                return await self._do_flush()
        if time.time() - self._last_flush > self._max_wait:
            async with self._lock:
                if self._queue:
                    return await self._do_flush()
        return None

    async def flush(self) -> Any:
        async with self._lock:
            if self._queue:
                return await self._do_flush()
        return None

    async def _do_flush(self) -> Any:
        items = list(self._queue)
        self._queue.clear()
        self._last_flush = time.time()
        if not items:
            return None
        return await self._flush(items)

    def size(self) -> int:
        return len(self._queue)


# ---------------------------------------------------------------------------
# Load tester
# ---------------------------------------------------------------------------


class LoadTester:
    """Runs a target function N times and reports latency statistics."""

    def __init__(self) -> None:
        self._results: List[float] = []

    async def run(
        self,
        target: Callable[[], Awaitable[Any]],
        *,
        iterations: int = 100,
        concurrency: int = 8,
    ) -> Dict[str, Any]:
        sem = asyncio.Semaphore(concurrency)
        self._results = []

        async def _one() -> None:
            async with sem:
                start = time.time()
                try:
                    await target()
                except Exception:
                    pass
                self._results.append((time.time() - start) * 1000)

        await asyncio.gather(*[_one() for _ in range(iterations)])
        return self._report()

    def _report(self) -> Dict[str, Any]:
        if not self._results:
            return {"iterations": 0}
        sorted_r = sorted(self._results)
        n = len(sorted_r)
        return {
            "iterations": n,
            "avg_ms": round(sum(sorted_r) / n, 4),
            "p50_ms": round(sorted_r[n // 2], 4),
            "p95_ms": round(sorted_r[min(n - 1, int(n * 0.95))], 4),
            "p99_ms": round(sorted_r[min(n - 1, int(n * 0.99))], 4),
            "max_ms": round(max(sorted_r), 4),
            "min_ms": round(min(sorted_r), 4),
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


_GLOBAL_PROFILER: Optional[Profiler] = None
_GLOBAL_CACHE: Optional[Cache] = None


def get_profiler() -> Profiler:
    global _GLOBAL_PROFILER
    if _GLOBAL_PROFILER is None:
        _GLOBAL_PROFILER = Profiler()
    return _GLOBAL_PROFILER


def get_cache() -> Cache:
    global _GLOBAL_CACHE
    if _GLOBAL_CACHE is None:
        _GLOBAL_CACHE = Cache()
    return _GLOBAL_CACHE