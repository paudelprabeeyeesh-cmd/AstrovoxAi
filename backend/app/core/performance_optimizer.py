"""Performance optimizer core utilities for inference pipelines."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PerformanceProfile:
    operation: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    device: str = "cpu"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def stop(self) -> None:
        self.end_time = time.time()

    @property
    def elapsed(self) -> float:
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time


class PerformanceOptimizer:
    def __init__(self):
        self._profiles: List[PerformanceProfile] = []
        self._running = False

    def profile(self, operation: str, device: str = "cpu", **metadata) -> "PerformanceOptimizer":
        self._current = PerformanceProfile(operation=operation, device=device, metadata=metadata)
        return self

    def __enter__(self) -> "PerformanceOptimizer":
        if hasattr(self, "_current") and self._current:
            pass
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if hasattr(self, "_current") and self._current:
            self._current.stop()
            self._profiles.append(self._current)

    def summarize(self) -> Dict[str, Any]:
        by_op: Dict[str, List[float]] = {}
        for p in self._profiles:
            by_op.setdefault(p.operation, []).append(p.elapsed)
        summary = {}
        for op, times in by_op.items():
            summary[op] = {
                "count": len(times),
                "mean_ms": sum(times) / len(times) * 1000,
                "min_ms": min(times) * 1000,
                "max_ms": max(times) * 1000,
            }
        return summary

    def clear(self) -> None:
        self._profiles.clear()
