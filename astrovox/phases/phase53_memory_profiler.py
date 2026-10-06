"""Memory profiler for Astrovox."""

from __future__ import annotations

import gc
import sys
from dataclasses import dataclass


@dataclass
class MemorySnapshot:
    """A memory snapshot."""
    allocated: float = 0.0
    objects: int = 0
    peak: float = 0.0


class MemoryProfiler:
    """Memory profiling."""

    def __init__(self):
        self.snapshots: list[MemorySnapshot] = []
        self.peak = 0.0

    def snapshot(self) -> MemorySnapshot:
        gc.collect()
        total = sys.getsizeof(gc.get_objects())
        if total > self.peak:
            self.peak = total
        snap = MemorySnapshot(allocated=total / (1024 * 1024), objects=len(gc.get_objects()),
                              peak=self.peak / (1024 * 1024))
        self.snapshots.append(snap)
        return snap

    def track(self, obj) -> MemorySnapshot:
        snap = self.snapshot()
        return snap

    def report(self) -> dict:
        if not self.snapshots:
            return {"peak_mb": 0.0, "snapshots": 0}
        return {"current_mb": self.snapshots[-1].allocated, "peak_mb": self.peak,
                "snapshots": len(self.snapshots)}

    def reset(self) -> None:
        self.snapshots.clear()
        self.peak = 0.0

    def count_objects(self, type_name: str | None = None) -> int:
        objects = gc.get_objects()
        if type_name is None:
            return len(objects)
        return sum(1 for o in objects if type(o).__name__ == type_name)
