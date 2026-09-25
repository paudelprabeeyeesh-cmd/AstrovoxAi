"""Memory leak detector with reusable class-based API."""

from __future__ import annotations

import gc
import logging
import tracemalloc
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MemoryLeakDetector:
    """Detect memory leaks by comparing snapshots."""

    def __init__(self, trace_frames: int = 25) -> None:
        self._trace_frames = trace_frames
        self._snapshots: Dict[str, Tuple[tracemalloc.Snapshot, tracemalloc.Snapshot]] = {}
        self._running = False

    def start(self) -> None:
        if not self._running:
            tracemalloc.start(self._trace_frames)
            self._running = True
            logger.info("Memory leak detection started")

    def stop(self) -> None:
        if self._running:
            tracemalloc.stop()
            self._running = False
            logger.info("Memory leak detection stopped")

    def snapshot(self) -> tracemalloc.Snapshot:
        gc.collect()
        return tracemalloc.take_snapshot()

    def diff(self, before: tracemalloc.Snapshot, after: tracemalloc.Snapshot, top_n: int = 20) -> List[Dict[str, Any]]:
        stats = after.compare_to(before, "lineno")
        top = stats[:top_n]
        results = []
        for stat in top:
            if stat.size_diff > 0:
                results.append({
                    "file": stat.traceback[0].filename if stat.traceback else "unknown",
                    "lineno": stat.traceback[0].lineno if stat.traceback else 0,
                    "size_diff_kb": round(stat.size_diff / 1024, 2),
                    "count_diff": stat.count_diff,
                })
        return results

    def detect(self, scenario_name: str, workload: Callable[[], Any]) -> List[Dict[str, Any]]:
        self.start()
        logger.info("Detecting memory leaks for scenario: %s", scenario_name)
        before = self.snapshot()
        workload()
        after = self.snapshot()
        results = self.diff(before, after)
        self.stop()
        return results

    def run_baseline(self) -> None:
        self.detect("baseline", lambda: None)

    def record(self, scenario_name: str, before: Optional[tracemalloc.Snapshot] = None, after: Optional[tracemalloc.Snapshot] = None) -> None:
        if before is None or after is None:
            logger.warning("Both snapshots are required for recording")
            return
        self._snapshots[scenario_name] = (before, after)
        logger.info("Recorded memory snapshot pair for scenario: %s", scenario_name)

    def get_recorded(self, scenario_name: str) -> Optional[Tuple[tracemalloc.Snapshot, tracemalloc.Snapshot]]:
        return self._snapshots.get(scenario_name)


memory_leak_detector = MemoryLeakDetector()
