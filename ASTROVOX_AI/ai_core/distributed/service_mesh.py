"""Service mesh integration for distributed inference traffic management."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ASTROVOX_AI.ai_core.distributed._base import validate_positive_float

logger = logging.getLogger(__name__)


class TrafficPolicy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    PASSTHROUGH = "passthrough"
    WEIGHTED = "weighted"


@dataclass
class ServiceMeshEndpoint:
    service: str
    host: str
    port: int
    region: str
    weight: int = 100
    healthy: bool = True
    connections: int = 0


class ServiceMeshClient:
    def __init__(self, mesh_provider: str = "istio", control_plane: str = "istiod:15012"):
        if not mesh_provider:
            raise ValueError("mesh_provider must not be empty")
        if not control_plane:
            raise ValueError("control_plane must not be empty")
        self.mesh_provider = mesh_provider
        self.control_plane = control_plane
        self._endpoints: Dict[str, List[ServiceMeshEndpoint]] = {}
        self._traffic_policies: Dict[str, TrafficPolicy] = {}
        self._round_robin_index: Dict[str, int] = {}

    def register_service(self, service: str, endpoints: List[ServiceMeshEndpoint]) -> None:
        if not service:
            raise ValueError("service must not be empty")
        if not endpoints:
            raise ValueError("endpoints must not be empty")
        self._endpoints[service] = endpoints
        logger.info("Registered %d endpoints for service %s", len(endpoints), service)

    def set_traffic_policy(self, service: str, policy: TrafficPolicy) -> None:
        if service not in self._endpoints:
            raise ValueError(f"service {service!r} not registered")
        self._traffic_policies[service] = policy
        logger.info("Set traffic policy for %s to %s", service, policy.value)

    def route_request(self, service: str, headers: Dict[str, str]) -> Optional[ServiceMeshEndpoint]:
        endpoints = [e for e in self._endpoints.get(service, []) if e.healthy]
        if not endpoints:
            logger.error("No healthy endpoints for service %s", service)
            return None
        policy = self._traffic_policies.get(service, TrafficPolicy.ROUND_ROBIN)
        if policy == TrafficPolicy.LEAST_CONNECTIONS:
            return min(endpoints, key=lambda e: e.connections)
        if policy == TrafficPolicy.PASSTHROUGH:
            return endpoints[0]
        if policy == TrafficPolicy.WEIGHTED:
            return max(endpoints, key=lambda e: e.weight)
        return self._round_robin(service, endpoints)

    def _round_robin(self, service: str, endpoints: List[ServiceMeshEndpoint]) -> ServiceMeshEndpoint:
        idx = self._round_robin_index.get(service, 0)
        endpoint = endpoints[idx % len(endpoints)]
        self._round_robin_index[service] = idx + 1
        return endpoint

    def configure_retries(self, service: str, attempts: int = 3, timeout: str = "2s") -> None:
        if service not in self._endpoints:
            raise ValueError(f"service {service!r} not registered")
        if attempts < 1:
            raise ValueError("attempts must be >= 1")
        logger.info("Configured retries for %s: %d attempts, timeout %s", service, attempts, timeout)

    def configure_circuit_breaker(self, service: str, threshold: int = 5, window: str = "30s") -> None:
        if service not in self._endpoints:
            raise ValueError(f"service {service!r} not registered")
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        logger.info("Configured circuit breaker for %s: threshold %d, window %s", service, threshold, window)

    def configure_fault_injection(self, service: str, abort_percentage: float = 0.0, delay_percentage: float = 0.0) -> None:
        if service not in self._endpoints:
            raise ValueError(f"service {service!r} not registered")
        if not 0.0 <= abort_percentage <= 100.0:
            raise ValueError("abort_percentage must be between 0 and 100")
        if not 0.0 <= delay_percentage <= 100.0:
            raise ValueError("delay_percentage must be between 0 and 100")
        logger.info("Configured fault injection for %s", service)

    def get_service_status(self) -> Dict[str, Any]:
        return {
            "provider": self.mesh_provider,
            "services": {
                service: {
                    "endpoints": len(endpoints),
                    "healthy": sum(1 for e in endpoints if e.healthy),
                    "traffic_policy": self._traffic_policies.get(service, TrafficPolicy.ROUND_ROBIN).value,
                }
                for service, endpoints in self._endpoints.items()
            },
        }
