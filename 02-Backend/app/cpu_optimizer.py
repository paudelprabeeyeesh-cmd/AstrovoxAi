"""CPU optimization for AstrovoxAI backend.

Provides CPU profiling, thread pool tuning, and process affinity management.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class CPUProfile:
    function_name: str
    total_time_ms: float
    call_count: int
    avg_time_ms: float
    max_time_ms: float


class CPUOptimizer:
    """Profiles CPU usage and optimizes thread/process allocation."""

    def __init__(self):
        self._profiles: Dict[str, List[float]] = {}
        self._process = psutil.Process(os.getpid())

    def profile_function(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = (time.perf_counter() - start) * 1000
                    self._profiles.setdefault(name, []).append(elapsed)
            return wrapper
        return decorator

    async def profile_async_function(self, name: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    elapsed = (time.perf_counter() - start) * 1000
                    self._profiles.setdefault(name, []).append(elapsed)
            return wrapper
        return decorator

    def get_profile_report(self) -> List[CPUProfile]:
        profiles = []
        for name, samples in self._profiles.items():
            profiles.append(
                CPUProfile(
                    function_name=name,
                    total_time_ms=sum(samples),
                    call_count=len(samples),
                    avg_time_ms=sum(samples) / len(samples) if samples else 0,
                    max_time_ms=max(samples) if samples else 0,
                )
            )
        return sorted(profiles, key=lambda p: p.total_time_ms, reverse=True)

    def get_recommended_thread_count(self) -> int:
        cpu_count = os.cpu_count() or 4
        cpu_percent = self._process.cpu_percent(interval=0.1)
        if cpu_percent > 80:
            return max(1, cpu_count // 2)
        if cpu_percent < 20:
            return cpu_count * 2
        return cpu_count

    def get_cpu_affinity(self) -> List[int]:
        try:
            return self._process.cpu_affinity()
        except Exception:  # noqa: BLE001
            return list(range(os.cpu_count() or 4))

    def set_cpu_affinity(self, cores: List[int]) -> bool:
        try:
            self._process.cpu_affinity(cores)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to set CPU affinity: %s", exc)
            return False

    def get_stats(self) -> Dict[str, Any]:
        cpu_percent = self._process.cpu_percent(interval=0.1)
        cpu_times = self._process.cpu_times()
        return {
            "cpu_percent": round(cpu_percent, 2),
            "user_time": round(cpu_times.user, 3),
            "system_time": round(cpu_times.system, 3),
            "threads": self._process.num_threads(),
            "recommended_threads": self.get_recommended_thread_count(),
            "profiled_functions": len(self._profiles),
            "hotspots": [
                {
                    "name": name,
                    "avg_ms": round(sum(samples) / len(samples), 3),
                    "calls": len(samples),
                }
                for name, samples in sorted(
                    self._profiles.items(),
                    key=lambda x: sum(x[1]),
                    reverse=True,
                )[:10]
            ],
        }


cpu_optimizer = CPUOptimizer()
