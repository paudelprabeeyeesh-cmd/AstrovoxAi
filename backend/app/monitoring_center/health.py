"""Health check management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    name: str
    check: Callable[[], bool]
    interval_seconds: float = 30.0
    last_status: HealthStatus = HealthStatus.HEALTHY
    last_checked: Optional[datetime] = None


class HealthCheckManager:
    def __init__(self) -> None:
        self._checks: Dict[str, HealthCheck] = {}

    def register(self, check: HealthCheck) -> None:
        self._checks[check.name] = check

    async def run_all(self) -> Dict[str, HealthStatus]:
        results = {}
        for name, check in self._checks.items():
            try:
                healthy = check.check()
                check.last_status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
            except Exception:
                check.last_status = HealthStatus.UNHEALTHY
            check.last_checked = datetime.now(timezone.utc)
            results[name] = check.last_status
        return results


health_check_manager = HealthCheckManager()
