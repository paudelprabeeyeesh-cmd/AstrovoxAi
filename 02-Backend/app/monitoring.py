"""Production monitoring — error tracking, performance monitoring, and uptime."""

import time
import logging
import traceback
import os
import platform
import sys
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ErrorEvent:
    """A tracked error event."""
    error_type: str
    message: str
    traceback: str
    timestamp: float
    endpoint: str = ""
    user_id: str = ""
    severity: str = "error"  # warning, error, critical


@dataclass
class PerformanceSnapshot:
    """System performance snapshot."""
    timestamp: float
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    open_files: int = 0
    thread_count: int = 0


class ErrorTracker:
    """Track and manage application errors."""

    def __init__(self, max_errors: int = 1000):
        self._errors: list[ErrorEvent] = []
        self._max_errors = max_errors
        self._error_counts: dict[str, int] = defaultdict(int)

    def track_error(
        self,
        error: Exception,
        endpoint: str = "",
        user_id: str = "",
        severity: str = "error",
    ):
        """Track an error event."""
        event = ErrorEvent(
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            timestamp=time.time(),
            endpoint=endpoint,
            user_id=user_id,
            severity=severity,
        )
        self._errors.append(event)
        self._error_counts[type(error).__name__] += 1

        if len(self._errors) > self._max_errors:
            self._errors = self._errors[-self._max_errors:]

        logger.error(f"Error tracked: {type(error).__name__}: {str(error)}")

    def get_errors(
        self,
        since: float = 0,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> list[ErrorEvent]:
        """Get tracked errors."""
        errors = [e for e in self._errors if e.timestamp >= since]
        if severity:
            errors = [e for e in errors if e.severity == severity]
        errors.sort(key=lambda e: e.timestamp, reverse=True)
        return errors[:limit]

    def get_error_summary(self) -> dict:
        """Get error summary statistics."""
        now = time.time()
        last_hour = now - 3600
        last_day = now - 86400

        return {
            "total_errors": len(self._errors),
            "last_hour": len([e for e in self._errors if e.timestamp >= last_hour]),
            "last_day": len([e for e in self._errors if e.timestamp >= last_day]),
            "by_type": dict(self._error_counts),
            "critical": len([e for e in self._errors if e.severity == "critical"]),
        }


class PerformanceMonitor:
    """Monitor system performance."""

    def __init__(self):
        self._snapshots: list[PerformanceSnapshot] = []
        self._request_times: dict[str, list[float]] = defaultdict(list)

    def record_request_time(self, endpoint: str, duration: float):
        """Record an API request time."""
        self._request_times[endpoint].append(duration)
        if len(self._request_times[endpoint]) > 1000:
            self._request_times[endpoint] = self._request_times[endpoint][-1000:]

    def get_request_stats(self, endpoint: str) -> dict:
        """Get request timing statistics."""
        times = self._request_times.get(endpoint, [])
        if not times:
            return {"count": 0}

        sorted_times = sorted(times)
        return {
            "count": len(times),
            "avg_ms": round(sum(times) / len(times) * 1000, 2),
            "min_ms": round(min(times) * 1000, 2),
            "max_ms": round(max(times) * 1000, 2),
            "p50_ms": round(sorted_times[len(times) // 2] * 1000, 2),
            "p95_ms": round(sorted_times[int(len(times) * 0.95)] * 1000, 2),
            "p99_ms": round(sorted_times[int(len(times) * 0.99)] * 1000, 2),
        }

    def get_system_stats(self) -> dict:
        """Get system resource usage."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            return {
                "cpu_percent": process.cpu_percent(),
                "memory_percent": process.memory_percent(),
                "memory_used_mb": round(mem_info.rss / 1024 / 1024, 2),
                "open_files": len(process.open_files()),
                "thread_count": process.num_threads(),
                "connections": len(process.connections()),
            }
        except ImportError:
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_mb": 0,
                "open_files": 0,
                "thread_count": 0,
                "note": "Install psutil for system stats",
            }

    def get_all_request_stats(self) -> dict:
        """Get stats for all endpoints."""
        return {
            endpoint: self.get_request_stats(endpoint)
            for endpoint in self._request_times
        }


class UptimeTracker:
    """Track application uptime."""

    def __init__(self):
        self._start_time = time.time()
        self._downtime_events: list[dict] = []

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def uptime_formatted(self) -> str:
        seconds = int(self.uptime_seconds)
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, secs = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    def get_uptime(self) -> dict:
        return {
            "start_time": datetime.fromtimestamp(self._start_time).isoformat(),
            "uptime_seconds": self.uptime_seconds,
            "uptime_formatted": self.uptime_formatted,
        }


error_tracker = ErrorTracker()
performance_monitor = PerformanceMonitor()
uptime_tracker = UptimeTracker()
