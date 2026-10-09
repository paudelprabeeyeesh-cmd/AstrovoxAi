"""
Service discovery and load balancing.

Provides service registry, health checks, and load balancing strategies.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class HealthStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()


@dataclass
class ServiceInstance:
    name: str
    host: str
    port: int
    health: HealthStatus = HealthStatus.HEALTHY
    load: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthCheckResult:
    instance: ServiceInstance
    status: HealthStatus
    latency_ms: float = 0.0
    error: Optional[str] = None


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: Dict[str, List[ServiceInstance]] = {}
        self._lock = threading.RLock()

    def register(self, instance: ServiceInstance) -> None:
        with self._lock:
            self._services.setdefault(instance.name, []).append(instance)

    def unregister(self, name: str, host: str, port: int) -> None:
        with self._lock:
            instances = self._services.get(name, [])
            self._services[name] = [i for i in instances if not (i.host == host and i.port == port)]

    def discover(self, name: str) -> List[ServiceInstance]:
        with self._lock:
            return list(self._services.get(name, []))

    def instances(self, name: str) -> List[ServiceInstance]:
        return self.discover(name)

    def health(self, name: str) -> List[HealthCheckResult]:
        results = []
        for inst in self.discover(name):
            results.append(HealthCheckResult(instance=inst, status=inst.health))
        return results


class LoadBalancer:
    def __init__(self, strategy: str = "round_robin") -> None:
        self.strategy = strategy
        self._round_robin: Dict[str, int] = {}

    def select(self, name: str, instances: List[ServiceInstance], registry: ServiceRegistry) -> Optional[ServiceInstance]:
        healthy = [i for i in instances if i.health == HealthStatus.HEALTHY]
        if not healthy:
            return None
        if self.strategy == "round_robin":
            idx = self._round_robin.get(name, 0) % len(healthy)
            self._round_robin[name] = idx + 1
            return healthy[idx]
        if self.strategy == "weighted":
            weights = [(i, max(1.0 - i.load, 0.01)) for i in healthy]
            total = sum(w for _, w in weights)
            pick = random.uniform(0, total)
            upto = 0.0
            for inst, weight in weights:
                upto += weight
                if pick <= upto:
                    return inst
            return healthy[-1]
        if self.strategy == "random":
            return random.choice(healthy)
        return healthy[0]

    def register_instance(self, name: str) -> None:
        self._round_robin.setdefault(name, 0)


class ServiceMesh:
    def __init__(self) -> None:
        self.registry = ServiceRegistry()
        self.balancer = LoadBalancer()

    def route(self, name: str) -> Optional[ServiceInstance]:
        instances = self.registry.discover(name)
        return self.balancer.select(name, instances, self.registry)

    def register(self, instance: ServiceInstance) -> None:
        self.registry.register(instance)
        self.balancer.register_instance(instance.name)

    def health_check(self, name: str) -> List[HealthCheckResult]:
        return self.registry.health(name)
