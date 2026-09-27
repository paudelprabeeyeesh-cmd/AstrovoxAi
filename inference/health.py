"""Health checks with model status for inference server."""

import os
import time
import psutil
import torch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthChecker:
    """Health checker with model status."""

    def __init__(self, engine: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        self.engine = engine
        self.config = config or {}
        self.startup_time = time.time()

    async def check_model_loaded(self) -> HealthCheck:
        """Check if model is loaded and ready."""
        if self.engine is None or not getattr(self.engine, "initialized", False):
            return HealthCheck(
                name="model_loaded",
                status=HealthStatus.UNHEALTHY,
                message="Model not loaded",
            )

        try:
            model = getattr(self.engine, "model", None)
            if model is None:
                return HealthCheck(
                    name="model_loaded",
                    status=HealthStatus.UNHEALTHY,
                    message="Model instance is None",
                )

            info = {
                "model_type": type(model).__name__,
                "device": str(getattr(self.engine, "device", "unknown")),
                "num_layers": getattr(model, "num_hidden_layers", "unknown"),
                "hidden_size": getattr(model, "hidden_size", "unknown"),
                "num_attention_heads": getattr(model, "num_attention_heads", "unknown"),
                "vocab_size": getattr(model, "vocab_size", "unknown"),
            }

            if torch.cuda.is_available():
                info["cuda_available"] = True
                info["cuda_device_count"] = torch.cuda.device_count()
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
            else:
                info["cuda_available"] = False

            return HealthCheck(
                name="model_loaded",
                status=HealthStatus.HEALTHY,
                message="Model loaded and ready",
                details=info,
            )
        except Exception as exc:
            return HealthCheck(
                name="model_loaded",
                status=HealthStatus.UNHEALTHY,
                message=f"Model check failed: {exc}",
            )

    async def check_memory(self) -> HealthCheck:
        """Check system memory."""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            usage_percent = mem.percent

            details = {
                "total_mb": round(mem.total / 1024 / 1024, 1),
                "used_mb": round(mem.used / 1024 / 1024, 1),
                "available_mb": round(mem.available / 1024 / 1024, 1),
                "percent": usage_percent,
                "swap_total_mb": round(swap.total / 1024 / 1024, 1),
                "swap_used_mb": round(swap.used / 1024 / 1024, 1),
                "swap_percent": swap.percent,
            }

            if torch.cuda.is_available():
                gpu_memory = []
                for i in range(torch.cuda.device_count()):
                    mem_allocated = torch.cuda.memory_allocated(i)
                    mem_total = torch.cuda.get_device_properties(i).total_memory
                    mem_reserved = torch.cuda.memory_reserved(i)
                    gpu_memory.append(
                        {
                            "device": i,
                            "name": torch.cuda.get_device_name(i),
                            "total_mb": round(mem_total / 1024 / 1024, 1),
                            "allocated_mb": round(mem_allocated / 1024 / 1024, 1),
                            "reserved_mb": round(mem_reserved / 1024 / 1024, 1),
                            "percent": round((mem_allocated / mem_total) * 100, 1)
                            if mem_total > 0
                            else 0,
                        }
                    )
                details["gpu_memory"] = gpu_memory

            status = HealthStatus.HEALTHY
            if usage_percent > 90:
                status = HealthStatus.UNHEALTHY
            elif usage_percent > 75:
                status = HealthStatus.DEGRADED

            return HealthCheck(
                name="memory",
                status=status,
                message=f"Memory usage: {usage_percent}%",
                details=details,
            )
        except Exception as exc:
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory check failed: {exc}",
            )

    async def check_disk(self) -> HealthCheck:
        """Check disk space."""
        try:
            disk = psutil.disk_usage("/")
            usage_percent = disk.percent

            details = {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": usage_percent,
            }

            status = HealthStatus.HEALTHY
            if usage_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif usage_percent > 85:
                status = HealthStatus.DEGRADED

            return HealthCheck(
                name="disk",
                status=status,
                message=f"Disk usage: {usage_percent}%",
                details=details,
            )
        except Exception as exc:
            return HealthCheck(
                name="disk",
                status=HealthStatus.UNHEALTHY,
                message=f"Disk check failed: {exc}",
            )

    async def check_uptime(self) -> HealthCheck:
        """Check uptime."""
        uptime = time.time() - self.startup_time
        return HealthCheck(
            name="uptime",
            status=HealthStatus.HEALTHY,
            message=f"Uptime: {uptime:.0f}s",
            details={"uptime_seconds": round(uptime, 1)},
        )

    async def check_cpu(self) -> HealthCheck:
        """Check CPU usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else None

            details = {
                "cpu_count": cpu_count,
                "cpu_percent": cpu_percent,
            }
            if load_avg:
                details["load_avg_1min"] = round(load_avg[0], 2)
                details["load_avg_5min"] = round(load_avg[1], 2)
                details["load_avg_15min"] = round(load_avg[2], 2)

            status = HealthStatus.HEALTHY
            if cpu_percent > 95:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 80:
                status = HealthStatus.DEGRADED

            return HealthCheck(
                name="cpu",
                status=status,
                message=f"CPU usage: {cpu_percent}%",
                details=details,
            )
        except Exception as exc:
            return HealthCheck(
                name="cpu",
                status=HealthStatus.UNHEALTHY,
                message=f"CPU check failed: {exc}",
            )

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return overall status."""
        checks = [
            await self.check_model_loaded(),
            await self.check_memory(),
            await self.check_disk(),
            await self.check_cpu(),
            await self.check_uptime(),
        ]

        overall_status = HealthStatus.HEALTHY
        for check in checks:
            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                break
            elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "checks": {
                check.name: {
                    "status": check.status.value,
                    "message": check.message,
                    "details": check.details,
                }
                for check in checks
            },
        }
