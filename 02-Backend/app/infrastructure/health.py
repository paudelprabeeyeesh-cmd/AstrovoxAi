"""Health check utilities."""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    message: str = ""
    last_check: str = ""


class HealthChecker:
    """Health check manager."""

    def __init__(self) -> None:
        self._components: Dict[str, ComponentHealth] = {}

    def register(self, name: str, check_func) -> None:
        """Register a health check function."""
        self._components[name] = ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
        )

    async def check_all(self) -> Dict[str, ComponentHealth]:
        """Run all health checks."""
        results = {}
        for name, component in self._components.items():
            try:
                start = time.time()
                result = await component.check_func()
                latency = (time.time() - start) * 1000
                component.latency_ms = latency
                component.status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                component.message = "OK" if result else "Check failed"
            except Exception as exc:
                component.status = HealthStatus.UNHEALTHY
                component.message = str(exc)
                logger.error(f"Health check failed for {name}: {exc}")
            results[name] = component
        return results

    def get_overall_status(self) -> HealthStatus:
        statuses = [c.status for c in self._components.values()]
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY


_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
