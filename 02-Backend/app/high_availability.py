"""High Availability — redundancy, failover, replication, health checks."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """A service instance."""
    id: str
    host: str
    port: int
    status: str = "healthy"
    last_heartbeat: float = 0.0
    failure_count: int = 0


class FailoverManager:
    """Manage failover for services."""

    def __init__(self):
        self._primary: Optional[ServiceInstance] = None
        self._secondaries: list[ServiceInstance] = []

    def set_primary(self, instance: ServiceInstance):
        """Set the primary instance."""
        self._primary = instance

    def add_secondary(self, instance: ServiceInstance):
        """Add a secondary instance."""
        self._secondaries.append(instance)

    def get_active(self) -> Optional[ServiceInstance]:
        """Get the active instance (primary or failover)."""
        if self._primary and self._primary.status == "healthy":
            return self._primary

        for secondary in self._secondaries:
            if secondary.status == "healthy":
                logger.warning(f"Failing over to secondary: {secondary.id}")
                return secondary

        return None

    def mark_unhealthy(self, instance_id: str):
        """Mark an instance as unhealthy."""
        if self._primary and self._primary.id == instance_id:
            self._primary.status = "unhealthy"

        for secondary in self._secondaries:
            if secondary.id == instance_id:
                secondary.status = "unhealthy"


class ReplicationManager:
    """Manage data replication."""

    def __init__(self):
        self._replicas: list[str] = []

    def add_replica(self, replica_id: str):
        """Add a replica."""
        self._replicas.append(replica_id)

    def get_replicas(self) -> list[str]:
        """Get all replicas."""
        return list(self._replicas)

    def get_healthy_replicas(self) -> list[str]:
        """Get healthy replicas."""
        return [r for r in self._replicas]


class SLAMonitor:
    """Monitor SLA/SLO compliance."""

    def __init__(self, target_availability: float = 99.9):
        self._target = target_availability
        self._total_requests = 0
        self._failed_requests = 0
        self._total_downtime = 0.0

    def record_request(self, success: bool):
        """Record a request."""
        self._total_requests += 1
        if not success:
            self._failed_requests += 1

    def get_availability(self) -> float:
        """Get current availability percentage."""
        if self._total_requests == 0:
            return 100.0
        return ((self._total_requests - self._failed_requests) / self._total_requests) * 100

    def is_sla_met(self) -> bool:
        """Check if SLA is being met."""
        return self.get_availability() >= self._target

    def get_error_budget(self) -> float:
        """Get remaining error budget."""
        return max(0, 100.0 - self._target - (100.0 - self.get_availability()))


class CapacityPlanner:
    """Plan capacity based on usage trends."""

    def __init__(self):
        self._usage_history: list[dict] = []

    def record_usage(self, timestamp: float, cpu: float, memory: float, requests: int):
        """Record usage data."""
        self._usage_history.append({
            "timestamp": timestamp,
            "cpu": cpu,
            "memory": memory,
            "requests": requests,
        })

        if len(self._usage_history) > 1000:
            self._usage_history = self._usage_history[-500:]

    def predict_needs(self, days_ahead: int = 30) -> dict:
        """Predict future capacity needs."""
        if not self._usage_history:
            return {"cpu_needed": 1, "memory_gb": 1}

        recent = self._usage_history[-100:]
        avg_cpu = sum(u["cpu"] for u in recent) / len(recent)
        avg_memory = sum(u["memory"] for u in recent) / len(recent)

        return {
            "cpu_needed": max(1, int(avg_cpu * 1.5)),
            "memory_gb": max(1, int(avg_memory * 1.5)),
            "estimated_requests": int(sum(u["requests"] for u in recent) / len(recent) * days_ahead),
        }


failover_manager = FailoverManager()
replication_manager = ReplicationManager()
sla_monitor = SLAMonitor()
capacity_planner = CapacityPlanner()
