"""Memory optimization for AstrovoxAI backend.

Provides memory profiling, reference tracking, and garbage collection hints.
"""

from __future__ import annotations

import gc
import logging
import os
import sys
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryStats:
    rss_mb: float
    vms_mb: float
    available_mb: float
    percent: float
    gc_collections: int
    timestamp: float


class MemoryOptimizer:
    """Monitors and optimizes memory usage."""

    def __init__(self, gc_threshold_mb: float = 512.0):
        self.gc_threshold_mb = gc_threshold_mb
        self._stats_history: List[MemoryStats] = []
        self._lock = threading.Lock()
        self._gc_counts = [0, 0, 0]

    def get_stats(self) -> MemoryStats:
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem = process.memory_info()
            vm = psutil.virtual_memory()
            gc_counts = gc.get_count()
            stats = MemoryStats(
                rss_mb=mem.rss / (1024 * 1024),
                vms_mb=mem.vms / (1024 * 1024),
                available_mb=vm.available / (1024 * 1024),
                percent=vm.percent,
                gc_collections=sum(gc_counts),
                timestamp=time.time(),
            )
            with self._lock:
                self._stats_history.append(stats)
                if len(self._stats_history) > 3600:
                    self._stats_history = self._stats_history[-3600:]
            return stats
        except Exception as exc:  # noqa: BLE001
            logger.error("Memory stats collection failed: %s", exc)
            return MemoryStats(rss_mb=0, vms_mb=0, available_mb=0, percent=0, gc_collections=0, timestamp=time.time())

    def maybe_gc(self, force: bool = False) -> Dict[str, int]:
        stats = self.get_stats()
        should_gc = force or stats.rss_mb > self.gc_threshold_mb
        if should_gc:
            before = len(gc.get_objects())
            collected = gc.collect()
            after = len(gc.get_objects())
            with self._lock:
                self._gc_counts = gc.get_count()
            logger.info("GC triggered: collected=%d, freed=%d objects", collected, before - after)
            return {"collected": collected, "freed_objects": before - after}
        return {"collected": 0, "freed_objects": 0}

    def drop_references(self, *objects: Any) -> None:
        for obj in objects:
            if hasattr(obj, "clear"):
                obj.clear()
            if hasattr(obj, "__dict__"):
                obj.__dict__.clear()
        self.maybe_gc()

    def get_memory_trend(self, window_minutes: int = 5) -> Dict[str, float]:
        with self._lock:
            if not self._stats_history:
                return {}
            cutoff = time.time() - (window_minutes * 60)
            recent = [s for s in self._stats_history if s.timestamp >= cutoff]
            if not recent:
                return {}
            rss_values = [s.rss_mb for s in recent]
            return {
                "current_rss_mb": rss_values[-1],
                "avg_rss_mb": sum(rss_values) / len(rss_values),
                "peak_rss_mb": max(rss_values),
                "min_rss_mb": min(rss_values),
                "trend": "increasing" if rss_values[-1] > rss_values[0] else "stable",
            }

    def get_stats_summary(self) -> Dict[str, Any]:
        with self._lock:
            if not self._stats_history:
                return {}
            latest = self._stats_history[-1]
            return {
                "rss_mb": round(latest.rss_mb, 2),
                "vms_mb": round(latest.vms_mb, 2),
                "available_mb": round(latest.available_mb, 2),
                "percent": round(latest.percent, 2),
                "gc_collections": latest.gc_collections,
                "sample_count": len(self._stats_history),
            }


memory_optimizer = MemoryOptimizer()
