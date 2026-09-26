"""Profiler for performance analysis."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ProfileReport:
    function_name: str
    calls: int
    total_time_ms: float
    avg_time_ms: float
    max_time_ms: float
    profile_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Profiler:
    def __init__(self) -> None:
        self._reports: List[ProfileReport] = []

    def profile(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000
            report = ProfileReport(
                function_name=func.__name__,
                calls=1,
                total_time_ms=elapsed,
                avg_time_ms=elapsed,
                max_time_ms=elapsed,
            )
            self._reports.append(report)
            return result
        return wrapper

    def get_reports(self) -> List[ProfileReport]:
        return list(self._reports)


profiler = Profiler()
