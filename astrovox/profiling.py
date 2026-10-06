"""Performance profiling utilities.

Provides lightweight profiling helpers for CPU-bound and memory-sensitive
code paths. Output is intentionally simple so it can be consumed by humans
and CI without extra dependencies.
"""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class ProfileResult:
    """One recorded profile sample."""

    name: str
    elapsed_ms: float = 0.0
    memory_bytes: int = 0


@dataclass
class ProfileReport:
    """Collected profile samples."""

    entries: list[ProfileResult] = field(default_factory=list)

    def add(self, entry: ProfileResult) -> None:
        self.entries.append(entry)

    def summary(self) -> str:
        lines = ["profile", "------"]
        for entry in self.entries:
            lines.append(
                f"{entry.name}: {entry.elapsed_ms:.3f}ms"
                f" | memory={entry.memory_bytes} bytes"
            )
        return "\n".join(lines)


class Profiler:
    """Context-managed profiler for named blocks."""

    def __init__(self, report: ProfileReport | None = None) -> None:
        self.report = report or ProfileReport()

    @contextlib.contextmanager
    def measure(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1e3
            memory_bytes = _current_memory_bytes()
            self.report.add(ProfileResult(name=name, elapsed_ms=elapsed_ms,
                                          memory_bytes=memory_bytes))

    def run(self, fn, name: str, *args, **kwargs):
        with self.measure(name):
            return fn(*args, **kwargs)


def _current_memory_bytes() -> int:
    try:
        import resource
        return resource.getrusp(resource.RUSAGE_SELF).ru_maxrss * 1024
    except Exception:
        return 0


def profile_function(fn, *args, **kwargs) -> tuple[Any, ProfileReport]:
    profiler = Profiler()
    result = profiler.run(fn, fn.__name__, *args, **kwargs)
    return result, profiler.report
