"""Monitoring module — error tracking, performance, GPU, memory, and uptime."""

from __future__ import annotations

import logging
import os
import platform
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ErrorRecord:
    error_type: str
    message: str
    endpoint: str = ""
    severity: str = "error"
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RequestMetric:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    user_id: str = ""
    model: str = ""
    provider: str = ""
    tokens: int = 0


@dataclass
class GPUMetric:
    device_id: int
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class MemoryMetric:
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float
    swap_used_mb: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# Error Tracker
# ============================================================================

class _ErrorTracker:
    _errors: deque = deque(maxlen=5000)
    _lock = threading.RLock()

    @classmethod
    def record_error(cls, error_type: str, message: str, endpoint: str = "", severity: str = "error", user_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        with cls._lock:
            record = ErrorRecord(
                error_type=error_type,
                message=message,
                endpoint=endpoint,
                severity=severity,
                user_id=user_id,
                metadata=metadata or {},
            )
            cls._errors.append(record)

    @classmethod
    def get_error_summary(cls) -> Dict[str, Any]:
        with cls._lock:
            total = len(cls._errors)
            by_severity: Dict[str, int] = defaultdict(int)
            by_type: Dict[str, int] = defaultdict(int)
            for e in cls._errors:
                by_severity[e.severity] += 1
                by_type[e.error_type] += 1
            return {
                "total": total,
                "by_severity": dict(sorted(by_severity.items(), key=lambda x: x[1], reverse=True)),
                "by_type": dict(sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:20]),
            }

    @classmethod
    def get_errors(cls, severity: Optional[str] = None, limit: int = 100) -> List[ErrorRecord]:
        with cls._lock:
            errors = list(cls._errors)
            if severity:
                errors = [e for e in errors if e.severity == severity]
            return errors[-limit:]

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._errors.clear()


# ============================================================================
# Performance Monitor
# ============================================================================

class _PerformanceMonitor:
    _request_history: deque = deque(maxlen=10000)
    _lock = threading.RLock()

    @classmethod
    def record_request(cls, metric: RequestMetric) -> None:
        with cls._lock:
            cls._request_history.append(metric)

    @classmethod
    def get_system_stats(cls) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "gpu": {
                "available": False,
                "devices": [],
                "utilization_percent": 0.0,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "temperature_c": 0.0,
            },
        }

        cpu = cls._get_cpu_percent()
        memory = cls._get_memory_info()
        disk = cls._get_disk_usage()

        stats["cpu"] = cpu
        stats["memory"] = memory["percent"] if memory else 0.0
        stats["disk"] = disk

        gpu_stats = cls._get_gpu_stats()
        stats["gpu"] = gpu_stats

        return stats

    @classmethod
    def get_all_request_stats(cls) -> Dict[str, Any]:
        with cls._lock:
            total = len(cls._request_history)
            errors = sum(1 for r in cls._request_history if r.status_code >= 400)
            latencies = [r.latency_ms for r in cls._request_history if r.latency_ms > 0]
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

            by_endpoint: Dict[str, int] = defaultdict(int)
            by_status: Dict[str, int] = defaultdict(int)
            by_method: Dict[str, int] = defaultdict(int)

            for r in cls._request_history:
                by_endpoint[r.endpoint] += 1
                by_status[str(r.status_code)] += 1
                by_method[r.method] += 1

            return {
                "total": total,
                "errors": errors,
                "error_rate": round(errors / max(total, 1), 4),
                "avg_latency_ms": round(avg_latency, 2),
                "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True)[:20]),
                "by_status": dict(sorted(by_status.items())),
                "by_method": dict(sorted(by_method.items())),
            }

    @classmethod
    def get_latency_metrics(cls, hours: int = 24) -> Dict[str, Any]:
        cutoff = time.time() - (hours * 3600)
        with cls._lock:
            recent = [r for r in cls._request_history if r.timestamp >= cutoff and r.latency_ms > 0]
        if not recent:
            return {"period_hours": hours, "count": 0, "avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
        latencies = sorted([r.latency_ms for r in recent])
        n = len(latencies)
        return {
            "period_hours": hours,
            "count": n,
            "avg_ms": round(sum(latencies) / n, 2),
            "min_ms": round(latencies[0], 2),
            "max_ms": round(latencies[-1], 2),
            "p50_ms": round(latencies[n // 2], 2),
            "p95_ms": round(latencies[int(n * 0.95)], 2),
            "p99_ms": round(latencies[int(n * 0.99)], 2),
        }

    @staticmethod
    def _get_cpu_percent() -> float:
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0

    @staticmethod
    def _get_memory_info() -> Optional[Dict[str, Any]]:
        try:
            import psutil
            vm = psutil.virtual_memory()
            return {
                "total_mb": round(vm.total / (1024 * 1024), 2),
                "used_mb": round(vm.used / (1024 * 1024), 2),
                "available_mb": round(vm.available / (1024 * 1024), 2),
                "percent": vm.percent,
            }
        except ImportError:
            return None

    @staticmethod
    def _get_disk_usage() -> float:
        try:
            import psutil
            return psutil.disk_usage("/").percent
        except ImportError:
            return 0.0

    @staticmethod
    def _get_gpu_stats() -> Dict[str, Any]:
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            devices = []
            total_util = 0.0
            total_mem_used = 0
            total_mem_total = 0
            max_temp = 0.0

            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except Exception:
                    temp = 0.0

                devices.append({
                    "device_id": i,
                    "name": pynvml.nvmlDeviceGetName(handle).decode("utf-8"),
                    "utilization_percent": util.gpu,
                    "memory_used_mb": round(mem.used / (1024 * 1024), 2),
                    "memory_total_mb": round(mem.total / (1024 * 1024), 2),
                    "temperature_c": temp,
                })

                total_util += util.gpu
                total_mem_used += mem.used
                total_mem_total += mem.total
                if temp > max_temp:
                    max_temp = temp

            pynvml.nvmlShutdown()
            return {
                "available": True,
                "devices": devices,
                "utilization_percent": round(total_util / max(device_count, 1), 2),
                "memory_used_mb": round(total_mem_used / (1024 * 1024), 2),
                "memory_total_mb": round(total_mem_total / (1024 * 1024), 2),
                "temperature_c": round(max_temp, 1),
            }
        except Exception:
            return {
                "available": False,
                "devices": [],
                "utilization_percent": 0.0,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "temperature_c": 0.0,
            }


# ============================================================================
# Uptime Tracker
# ============================================================================

class _UptimeTracker:
    _start_time: float = field(default_factory=time.time)
    _status: str = "healthy"

    @classmethod
    def get_uptime(cls) -> Dict[str, Any]:
        uptime_seconds = time.time() - cls._start_time
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "start_time": cls._start_time,
            "status": cls._status,
        }

    @classmethod
    def set_status(cls, status: str) -> None:
        cls._status = status

    @classmethod
    def start(cls) -> None:
        cls._start_time = time.time()
        cls._status = "healthy"


error_tracker = _ErrorTracker()
performance_monitor = _PerformanceMonitor()
uptime_tracker = _UptimeTracker()
uptime_tracker.start()
