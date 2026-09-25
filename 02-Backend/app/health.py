import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

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
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=latency,
            )

    def check_redis(self) -> ComponentHealth:
        start = time.time()
        try:
            if hasattr(self.app.state, "redis") and self.app.state.redis:
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
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message=str(e),
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
                import os

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
            except Exception as e:
                latency = (time.time() - start) * 1000
                results[name] = ComponentHealth(
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    latency_ms=latency,
                )
        return results

    def check_storage(self) -> ComponentHealth:
        start = time.time()
        try:
            from app.storage import get_storage_backend
            backend = get_storage_backend()
            backend.health_check()
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                message="Storage backend connected",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=str(e),
                latency_ms=latency,
            )

    def get_overall_health(self) -> Dict[str, Any]:
        db = self.check_database()
        redis = self.check_redis()
        storage = self.check_storage()
        llm = self.check_llm_providers()

        components = {
            "database": {
                "status": db.status.value,
                "message": db.message,
                "latency_ms": db.latency_ms,
            },
            "redis": {
                "status": redis.status.value,
                "message": redis.message,
                "latency_ms": redis.latency_ms,
            },
            "storage": {
                "status": storage.status.value,
                "message": storage.message,
                "latency_ms": storage.latency_ms,
            },
            "llm_providers": {
                name: {
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for name, c in llm.items()
            },
        }

        statuses = [db.status, redis.status, storage.status] + [
            c.status for c in llm.values()
        ]
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.DEGRADED

        return {
            "status": overall.value,
            "components": components,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
