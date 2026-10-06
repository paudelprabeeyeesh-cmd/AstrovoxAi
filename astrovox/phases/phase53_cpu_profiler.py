"""CPU and time profiling."""

from __future__ import annotations

import cProfile
import io
import pstats
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProfileResult:
    """A profiling result."""
    stats: dict = field(default_factory=dict)
    top: list[str] = field(default_factory=list)


class CPUProfiler:
    """CPU profiling."""

    def __init__(self):
        self.profiler = cProfile.Profile()
        self.results: list[ProfileResult] = []

    def start(self) -> None:
        self.profiler.enable()

    def stop(self) -> ProfileResult:
        self.profiler.disable()
        buffer = io.StringIO()
        ps = pstats.Stats(self.profiler, stream=buffer).sort_stats("cumulative")
        ps.print_stats(20)
        top = [l for l in buffer.getvalue().splitlines()[:10]]
        result = ProfileResult(stats={"total_calls": ps.total_calls, "tottime": ps.total_tt},
                               top=top)
        self.results.append(result)
        return result

    def run(self, fn, *args, **kwargs) -> tuple[Any, ProfileResult]:
        self.start()
        result = fn(*args, **kwargs)
        profile = self.stop()
        return result, profile

    def get_stats(self, idx: int = -1) -> ProfileResult:
        if idx < 0:
            idx += len(self.results)
        return self.results[idx]
