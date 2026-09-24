"""
System-wide performance optimization.

Profiles components, detects bottlenecks, and applies optimization strategies.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ProfileEntry:
    component: str
    duration_ms: float
    timestamp: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bottleneck:
    component: str
    avg_duration_ms: float
    count: int
    severity: str


class Profiler:
    def __init__(self) -> None:
        self._entries: List[ProfileEntry] = []
        self._lock = threading.RLock()
        self._enabled = True

    def record(self, entry: ProfileEntry) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._entries.append(entry)

    def report(self) -> List[Bottleneck]:
        with self._lock:
            data: Dict[str, List[float]] = {}
            for e in self._entries:
                data.setdefault(e.component, []).append(e.duration_ms)
        results = []
        for component, durations in data.items():
            avg = sum(durations) / len(durations)
            severity = "high" if avg > 200.0 else "medium" if avg > 50.0 else "low"
            results.append(Bottleneck(component=component, avg_duration_ms=avg, count=len(durations), severity=severity))
        return sorted(results, key=lambda b: b.avg_duration_ms, reverse=True)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False


class PerformanceOptimizer:
    def __init__(self, profiler: Profiler) -> None:
        self.profiler = profiler
        self._strategies: Dict[str, Callable[[], None]] = {}

    def register_strategy(self, component: str, strategy: Callable[[], None]) -> None:
        self._strategies[component] = strategy

    def apply(self, component: str) -> None:
        strategy = self._strategies.get(component)
        if strategy:
            strategy()

    def optimize_all(self, thresholds: Optional[Dict[str, float]] = None) -> List[str]:
        thresholds = thresholds or {}
        optimized = []
        for bottleneck in self.profiler.report():
            threshold = thresholds.get(bottleneck.component, 50.0)
            if bottleneck.avg_duration_ms >= threshold:
                self.apply(bottleneck.component)
                optimized.append(bottleneck.component)
        return optimized


class ConnectionPool:
    def __init__(self, max_size: int = 10) -> None:
        self._max_size = max_size
        self._pool: List[Any] = []
        self._lock = threading.Lock()

    def acquire(self) -> Any:
        with self._lock:
            if self._pool:
                return self._pool.pop(0)
        return None

    def release(self, connection: Any) -> None:
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(connection)

    def size(self) -> int:
        with self._lock:
            return len(self._pool)


class BatchProcessor:
    def __init__(self, batch_size: int = 100) -> None:
        self.batch_size = batch_size
        self._queue: List[Any] = []
        self._lock = threading.Lock()

    def submit(self, item: Any) -> None:
        with self._lock:
            self._queue.append(item)
            if len(self._queue) >= self.batch_size:
                self._flush()

    def _flush(self) -> None:
        batch = self._queue[:self.batch_size]
        self._queue = self._queue[self.batch_size:]
        for item in batch:
            try:
                self._process(item)
            except Exception:
                continue

    def _process(self, item: Any) -> None:
        pass
