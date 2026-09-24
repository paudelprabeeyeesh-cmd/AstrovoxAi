import dataclasses
import gc
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple


@dataclass
class MemorySnapshot:
    rss_mb: float
    allocations: int
    references: int


def _rss_mb() -> float:
    try:
        with open(f"/proc/{os.getpid()}/status") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    return _fallback_rss_mb()


def _fallback_rss_mb() -> float:
    try:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return 0.0


def _allocations() -> int:
    return sum(len(gc.get_objects()) for _ in [0])


def _references() -> int:
    return sum(
        1
        for obj in gc.get_objects()
        if isinstance(obj, (dict, list, tuple)) and sys.getrefcount(obj) > 2
    )


def take_snapshot() -> MemorySnapshot:
    return MemorySnapshot(
        rss_mb=_rss_mb(),
        allocations=_allocations(),
        references=_references(),
    )


def _snapshot_diff(before: MemorySnapshot, after: MemorySnapshot) -> Dict[str, float]:
    return {
        "rss_mb_delta": after.rss_mb - before.rss_mb,
        "allocations_delta": after.allocations - before.allocations,
        "references_delta": after.references - before.references,
    }


def _drop_references(obj: Any) -> None:
    if hasattr(obj, "clear"):
        obj.clear()
    if hasattr(obj, "__dict__"):
        obj.__dict__.clear()


def drop_references(objects: List[Any]) -> None:
    for obj in objects:
        _drop_references(obj)
    gc.collect()


def compress_references(obj: Any) -> Optional[int]:
    before = sum(len(item) for item in obj) if hasattr(obj, "__len__") else len(obj)
    _drop_references(obj)
    gc.collect()
    after = sum(len(item) for item in obj) if hasattr(obj, "__len__") else len(obj)
    return max(0, before - after)


def optimize_memory(
    func: Callable[..., Any], objects: List[Any]
) -> Tuple[Any, Dict[str, float]]:
    before = take_snapshot()
    result = func()
    after = func()
    memory_after = take_snapshot()
    drop_references(objects)
    memory_final = take_snapshot()
    return result, {
        "rss_mb": memory_after.rss_mb,
        "allocations": memory_after.allocations,
        "rss_delta": memory_final.rss_mb - memory_after.rss_mb,
        "allocations_delta": memory_final.allocations - memory_after.allocations,
    }


@dataclass
class MemoryReport:
    baseline_mb: float
    peak_mb: float
    reclaimed_mb: float
    retained_mb: float


def report_memory(snapshot: MemorySnapshot) -> str:
    return (
        f"RSS: {snapshot.rss_mb:.2f} MB | "
        f"Allocations: {snapshot.allocations} | "
        f"References: {snapshot.references}"
    )


def to_json(snapshot: MemorySnapshot) -> str:
    return json.dumps(dataclasses.asdict(snapshot))


def describe() -> str:
    return (
        "Memory optimizer: monitor RSS, drop references, compress containers, "
        "and trigger garbage collection."
    )
