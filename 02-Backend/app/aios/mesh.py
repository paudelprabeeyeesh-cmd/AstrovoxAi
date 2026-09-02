"""Service mesh: service registry, discovery, health checks, versioning."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import make_id, now, now_iso


class ServiceState(str, Enum):
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"
    STOPPED = "stopped"


@dataclass
class ServiceInstance:
    id: str
    name: str
    version: str
    host: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: ServiceState = ServiceState.STARTING
    last_heartbeat: float = field(default_factory=now)
    last_health_check: float = field(default_factory=now)
    started_at: float = field(default_factory=now)
    region: str = "default"
    zone: str = "default"
    weight: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "host": self.host,
            "port": self.port,
            "metadata": self.metadata,
            "state": self.state.value,
            "last_heartbeat": self.last_heartbeat,
            "last_health_check": self.last_health_check,
            "started_at": self.started_at,
            "uptime_s": round(now() - self.started_at, 2),
            "region": self.region,
            "zone": self.zone,
            "weight": self.weight,
        }


class HealthCheck:
    """Lightweight health probe. Real impls hit an HTTP endpoint."""

    def __init__(self, fn: Optional[Callable[[ServiceInstance], bool]] = None) -> None:
        self.fn = fn or self._default

    def _default(self, instance: ServiceInstance) -> bool:
        return instance.state in {ServiceState.HEALTHY, ServiceState.DEGRADED}

    def check(self, instance: ServiceInstance) -> bool:
        instance.last_health_check = now()
        ok = self.fn(instance)
        if not ok:
            instance.state = ServiceState.UNHEALTHY
        return ok


class ServiceRegistry:
    """In-process service registry. A real deployment backs this with etcd/Consul."""

    def __init__(self, health_check: Optional[HealthCheck] = None) -> None:
        self._instances: Dict[str, ServiceInstance] = {}
        self._checks: Dict[str, HealthCheck] = defaultdict(lambda: health_check or HealthCheck())
        self._heartbeat_timeout = 30.0

    def register(self, instance: ServiceInstance) -> ServiceInstance:
        instance.id = instance.id or make_id("svc")
        instance.state = ServiceState.HEALTHY
        instance.last_heartbeat = now()
        self._instances[instance.id] = instance
        return instance

    def deregister(self, instance_id: str) -> Optional[ServiceInstance]:
        return self._instances.pop(instance_id, None)

    def heartbeat(self, instance_id: str) -> bool:
        inst = self._instances.get(instance_id)
        if not inst:
            return False
        inst.last_heartbeat = now()
        return True

    def discover(self, name: str, only_healthy: bool = True) -> List[ServiceInstance]:
        out = [i for i in self._instances.values() if i.name == name]
        if only_healthy:
            out = [i for i in out if i.state == ServiceState.HEALTHY]
        out.sort(key=lambda i: i.weight, reverse=True)
        return out

    def pick(self, name: str) -> Optional[ServiceInstance]:
        candidates = self.discover(name)
        if not candidates:
            return None
        # Weighted round-robin
        total = sum(max(c.weight, 1) for c in candidates) or 1
        target = (now() * 1000) % total
        running = 0
        for c in candidates:
            running += max(c.weight, 1)
            if running >= target:
                return c
        return candidates[0]

    def run_health_checks(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for inst in list(self._instances.values()):
            check = self._checks[inst.name]
            ok = check.check(inst)
            results.append(
                {
                    "id": inst.id,
                    "name": inst.name,
                    "ok": ok,
                    "state": inst.state.value,
                    "ts": now(),
                }
            )
        return results

    def evict_stale(self, timeout: Optional[float] = None) -> List[str]:
        limit = timeout or self._heartbeat_timeout
        stale = [
            i.id
            for i in self._instances.values()
            if now() - i.last_heartbeat > limit
        ]
        for sid in stale:
            inst = self._instances.pop(sid, None)
            if inst:
                inst.state = ServiceState.UNHEALTHY
        return stale

    def list(self) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._instances.values()]

    def stats(self) -> Dict[str, Any]:
        by_state: Dict[str, int] = defaultdict(int)
        by_name: Dict[str, int] = defaultdict(int)
        for inst in self._instances.values():
            by_state[inst.state.value] += 1
            by_name[inst.name] += 1
        return {
            "total": len(self._instances),
            "by_state": dict(by_state),
            "by_name": dict(by_name),
        }


_GLOBAL_REGISTRY: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ServiceRegistry()
    return _GLOBAL_REGISTRY


def seed_default_services() -> None:
    """Populate the registry with logical services for the platform."""

    registry = get_service_registry()
    if registry.list():
        return
    defaults = [
        ("chat", "1.0.0", "chat-service"),
        ("memory", "1.0.0", "memory-service"),
        ("knowledge", "1.0.0", "knowledge-service"),
        ("agent", "1.0.0", "agent-service"),
        ("search", "1.0.0", "search-service"),
        ("embedding", "1.0.0", "embedding-service"),
        ("evaluation", "1.0.0", "evaluation-service"),
        ("workflow", "1.0.0", "workflow-service"),
        ("notification", "1.0.0", "notification-service"),
        ("billing", "1.0.0", "billing-service"),
    ]
    for name, version, host in defaults:
        for i in range(2):
            registry.register(
                ServiceInstance(
                    id="",
                    name=name,
                    version=version,
                    host=host,
                    port=8000 + i,
                    metadata={"shard": i, "role": "primary" if i == 0 else "secondary"},
                )
            )