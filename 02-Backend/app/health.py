import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    status: HealthStatus
    message: str
    latency_ms: float = 0.0
    details: Optional[Dict[str, Any]] = None


class HealthCheckService:
    def __init__(self, app: Optional[Any] = None) -> None:
        self.app = app
        self._history: list = []

    def check_database(self) -> ComponentHealth:
        start = time.time()
        try:
            from app.database import get_db

            with get_db() as conn:
                conn.execute("SELECT 1")
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Database connected",
                latency_ms=latency,
            )
        except Exception as _e:  # noqa: BLE001
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(_e),
                latency_ms=latency,
            )

    def check_redis(self) -> ComponentHealth:
        start = time.time()
        try:
            if hasattr(self.app, "state") and hasattr(self.app.state, "redis") and self.app.state.redis:
                self.app.state.redis.ping()
                latency = (time.time() - start) * 1000
                return ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    message="Redis connected",
                    latency_ms=latency,
                )
            return ComponentHealth(
                status=HealthStatus.DEGRADED, message="Redis not configured"
            )
        except Exception as _e:  # noqa: BLE001
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(_e),
                latency_ms=latency,
            )

    def check_llm_providers(self) -> Dict[str, ComponentHealth]:
        results: Dict[str, ComponentHealth] = {}
        providers = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        for name, env_var in providers.items():
            start = time.time()
            try:
                if not os.getenv(env_var):
                    results[name] = ComponentHealth(
                        status=HealthStatus.DEGRADED,
                        message="API key not configured",
                    )
                    continue
                results[name] = ComponentHealth(
                    status=HealthStatus.HEALTHY,
                    message="API key configured",
                )
            except Exception as _e:  # noqa: BLE001
                latency = (time.time() - start) * 1000
                results[name] = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    message=str(_e),
                    latency_ms=latency,
                )
        return results

    def check_memory(self) -> ComponentHealth:
        start = time.time()
        try:
            import psutil
            mem = psutil.virtual_memory()
            avail_pct = mem.available / mem.total * 100
            latency = (time.time() - start) * 1000
            if avail_pct < 10:
                status = HealthStatus.UNHEALTHY
                message = f"Memory critically low: {avail_pct:.1f}% available"
            elif avail_pct < 25:
                status = HealthStatus.DEGRADED
                message = f"Memory constrained: {avail_pct:.1f}% available"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory OK: {avail_pct:.1f}% available"
            return ComponentHealth(
                status=status,
                message=message,
                latency_ms=latency,
                details={
                    "total_mb": round(mem.total / 1024 / 1024, 1),
                    "available_mb": round(mem.available / 1024 / 1024, 1),
                    "percent_used": round(mem.percent, 1),
                },
            )
        except ImportError:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="psutil not installed; memory check skipped",
            )
        except Exception as _e:  # noqa: BLE001
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(_e),
                latency_ms=latency,
            )

    def check_disk(self) -> ComponentHealth:
        start = time.time()
        try:
            import psutil
            disk = psutil.disk_usage("/")
            free_pct = disk.free / disk.total * 100
            latency = (time.time() - start) * 1000
            if free_pct < 5:
                status = HealthStatus.UNHEALTHY
                message = f"Disk critically low: {free_pct:.1f}% free"
            elif free_pct < 15:
                status = HealthStatus.DEGRADED
                message = f"Disk constrained: {free_pct:.1f}% free"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk OK: {free_pct:.1f}% free"
            return ComponentHealth(
                status=status,
                message=message,
                latency_ms=latency,
                details={
                    "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                    "percent_used": round(disk.percent, 1),
                },
            )
        except ImportError:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="psutil not installed; disk check skipped",
            )
        except Exception as _e:  # noqa: BLE001
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(_e),
                latency_ms=latency,
            )

    def get_overall_health(self) -> Dict[str, Any]:
        db = self.check_database()
        redis = self.check_redis()
        llm = self.check_llm_providers()
        memory = self.check_memory()
        disk = self.check_disk()

        components = {
            "database": {
                "status": db.status.value,
                "message": db.message,
                "latency_ms": db.latency_ms,
                "details": db.details,
            },
            "redis": {
                "status": redis.status.value,
                "message": redis.message,
                "latency_ms": redis.latency_ms,
                "details": redis.details,
            },
            "memory": {
                "status": memory.status.value,
                "message": memory.message,
                "latency_ms": memory.latency_ms,
                "details": memory.details,
            },
            "disk": {
                "status": disk.status.value,
                "message": disk.message,
                "latency_ms": disk.latency_ms,
                "details": disk.details,
            },
            "llm_providers": {
                name: {
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "details": c.details,
                }
                for name, c in llm.items()
            },
        }

        statuses = [db.status, redis.status, memory.status, disk.status] + [
            c.status for c in llm.values()
        ]

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.UNHEALTHY
        else:
            overall = HealthStatus.DEGRADED

        payload = {
            "status": overall.value,
            "components": components,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        self._history.append(payload)
        if len(self._history) > 100:
            self._history.pop(0)
        return payload

    def history(self):
        return list(self._history)

    def is_healthy(self) -> bool:
        try:
            return self.get_overall_health()["status"] == "healthy"
        except Exception as _e:  # noqa: BLE001
            return False


health_service = HealthCheckService()
