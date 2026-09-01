"""Enhanced monitoring dashboard with system metrics."""

import time
import logging
import os
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_usage_percent: float = 0.0
    open_connections: int = 0
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    total_requests: int = 0
    total_errors: int = 0
    active_users: int = 0
    total_users: int = 0
    total_conversations: int = 0
    total_messages: int = 0
    ai_requests: int = 0
    ai_tokens_used: int = 0
    ai_cost_total: float = 0.0
    avg_ai_latency_ms: float = 0.0
    uptime_seconds: float = 0.0


class MetricsCollector:
    """Collect and aggregate system and application metrics."""

    def __init__(self):
        self._start_time = time.time()
        self._request_times: list[float] = []
        self._error_count = 0
        self._request_count = 0

    def record_request(self, duration: float, is_error: bool = False):
        """Record a request."""
        self._request_count += 1
        self._request_times.append(duration)
        if is_error:
            self._error_count += 1

        if len(self._request_times) > 10000:
            self._request_times = self._request_times[-5000:]

    def get_system_metrics(self) -> SystemMetrics:
        """Get system metrics."""
        metrics = SystemMetrics()

        try:
            import psutil
            metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            metrics.memory_percent = mem.percent
            metrics.memory_used_mb = mem.used / 1024 / 1024
            metrics.memory_total_mb = mem.total / 1024 / 1024
            disk = psutil.disk_usage("/")
            metrics.disk_usage_percent = disk.percent
        except ImportError:
            pass

        return metrics

    def get_application_metrics(self) -> ApplicationMetrics:
        """Get application metrics."""
        metrics = ApplicationMetrics()
        metrics.uptime_seconds = time.time() - self._start_time
        metrics.total_requests = self._request_count
        metrics.total_errors = self._error_count

        if self._request_times:
            metrics.avg_response_time_ms = (
                sum(self._request_times) / len(self._request_times) * 1000
            )

        return metrics

    def get_full_dashboard(self) -> dict:
        """Get complete dashboard data."""
        system = self.get_system_metrics()
        app = self.get_application_metrics()

        return {
            "timestamp": time.time(),
            "system": {
                "cpu_percent": round(system.cpu_percent, 1),
                "memory_percent": round(system.memory_percent, 1),
                "memory_used_mb": round(system.memory_used_mb, 1),
                "memory_total_mb": round(system.memory_total_mb, 1),
                "disk_usage_percent": round(system.disk_usage_percent, 1),
            },
            "application": {
                "uptime_seconds": round(app.uptime_seconds),
                "total_requests": app.total_requests,
                "total_errors": app.total_errors,
                "avg_response_time_ms": round(app.avg_response_time_ms, 2),
                "requests_per_minute": round(
                    app.total_requests / max(app.uptime_seconds / 60, 1), 1
                ),
                "error_rate": round(
                    app.total_errors / max(app.total_requests, 1) * 100, 2
                ),
            },
        }


metrics_collector = MetricsCollector()
