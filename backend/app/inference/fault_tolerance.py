"""Fault tolerance for distributed inference nodes."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    node_id: str
    status: HealthStatus
    latency_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class FaultToleranceManager:
    def __init__(
        self,
        node_ids: List[str],
        health_check_fn: Callable[[str], Dict[str, Any]],
        failure_callback: Optional[Callable[[str], None]] = None,
        recovery_callback: Optional[Callable[[str], None]] = None,
    ):
        self.node_ids = node_ids
        self.health_check_fn = health_check_fn
        self.failure_callback = failure_callback
        self.recovery_callback = recovery_callback
        self._health_history: Dict[str, List[HealthCheckResult]] = {nid: [] for nid in node_ids}
        self._node_status: Dict[str, HealthStatus] = {nid: HealthStatus.HEALTHY for nid in node_ids}
        self._failure_counts: Dict[str, int] = {nid: 0 for nid in node_ids}
        self._recovery_counts: Dict[str, int] = {nid: 0 for nid in node_ids}

    def run_health_checks(self) -> List[HealthCheckResult]:
        results = []
        for node_id in self.node_ids:
            start = time.time()
            try:
                details = self.health_check_fn(node_id)
                latency = (time.time() - start) * 1000
                if details.get("healthy", False):
                    status = HealthStatus.HEALTHY
                    self._failure_counts[node_id] = 0
                elif details.get("degraded", False):
                    status = HealthStatus.DEGRADED
                else:
                    status = HealthStatus.UNHEALTHY
                    self._failure_counts[node_id] += 1
            except Exception as exc:
                latency = (time.time() - start) * 1000
                status = HealthStatus.UNHEALTHY
                details = {"error": str(exc)}
                self._failure_counts[node_id] += 1
            result = HealthCheckResult(
                node_id=node_id,
                status=status,
                latency_ms=latency,
                timestamp=datetime.utcnow(),
                details=details,
            )
            results.append(result)
            self._health_history[node_id].append(result)
            self._node_status[node_id] = status
            if status == HealthStatus.UNHEALTHY and self._failure_counts[node_id] >= 3:
                if self.failure_callback:
                    self.failure_callback(node_id)
            elif status == HealthStatus.HEALTHY and self._node_status[node_id] != HealthStatus.HEALTHY:
                self._recovery_counts[node_id] += 1
                if self.recovery_callback:
                    self.recovery_callback(node_id)
                self._node_status[node_id] = HealthStatus.HEALTHY
        return results

    def get_node_status(self, node_id: str) -> HealthStatus:
        return self._node_status.get(node_id, HealthStatus.UNHEALTHY)

    def get_unhealthy_nodes(self) -> List[str]:
        return [nid for nid, status in self._node_status.items() if status != HealthStatus.HEALTHY]

    def get_health_summary(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.node_ids),
            "healthy": sum(1 for s in self._node_status.values() if s == HealthStatus.HEALTHY),
            "degraded": sum(1 for s in self._node_status.values() if s == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for s in self._node_status.values() if s == HealthStatus.UNHEALTHY),
            "failure_counts": dict(self._failure_counts),
            "recovery_counts": dict(self._recovery_counts),
        }

    def get_node_history(self, node_id: str, limit: int = 10) -> List[HealthCheckResult]:
        return self._health_history.get(node_id, [])[-limit:]
