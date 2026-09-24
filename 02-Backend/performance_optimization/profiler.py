import contextlib
import dataclasses
import functools
import json
import statistics
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple


@dataclass
class ProfileRecord:
    name: str
    iterations: int
    total_seconds: float
    per_iteration_ms: float
    per_iteration_min_ms: float
    per_iteration_max_ms: float
    per_iteration_median_ms: float
    per_iteration_std_ms: float


class Profiler:
    def __init__(self) -> None:
        self._records: Dict[str, List[float]] = defaultdict(list)

    def record(self, name: str, elapsed: float) -> None:
        self._records[name].append(elapsed)

    def report(self, as_json: bool = False) -> Any:
        entries = []
        for name, samples in self._records.items():
            iterations = len(samples)
            total_seconds = sum(samples)
            per_iteration_ms = statistics.mean(samples) * 1000.0
            per_iteration_min_ms = min(samples) * 1000.0
            per_iteration_max_ms = max(samples) * 1000.0
            per_iteration_median_ms = statistics.median(samples) * 1000.0
            per_iteration_std_ms = statistics.pstdev(samples) * 1000.0
            entries.append(
                ProfileRecord(
                    name=name,
                    iterations=iterations,
                    total_seconds=total_seconds,
                    per_iteration_ms=per_iteration_ms,
                    per_iteration_min_ms=per_iteration_min_ms,
                    per_iteration_max_ms=per_iteration_max_ms,
                    per_iteration_median_ms=per_iteration_median_ms,
                    per_iteration_std_ms=per_iteration_std_ms,
                )
            )
        entries.sort(key=lambda r: r.total_seconds, reverse=True)
        if as_json:
            return json.dumps([dataclasses.asdict(e) for e in entries])
        return entries

    @contextmanager
    def timer(self, name: str) -> Generator[None, None, None]:
        start = time.perf_counter()
        yield
        elapsed = time.perf_counter() - start
        self.record(name, elapsed)

    def wrap_function(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            profiler = self

            @functools.wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                with profiler.timer(name):
                    return func(*args, **kwargs)

            return wrapped

        return decorator

    def reset(self) -> None:
        self._records.clear()
