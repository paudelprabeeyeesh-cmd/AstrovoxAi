"""Service mesh integration for distributed AI services."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TrafficPolicy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_REQUEST = "least_request"
    RANDOM = "random"
    PASSTHROUGH = "passthrough"


class OutlierDetection:
    consecutive_5xx: int = 5
    interval: str = "30s"
    base_ejection_time: str = "30s"


@dataclass
class ServiceMeshConfig:
    service_name: str
    namespace: str = "astrovox"
    port: int = 8000
    traffic_policy: TrafficPolicy = TrafficPolicy.LEAST_REQUEST
    outlier_detection: OutlierDetection = field(default_factory=OutlierDetection)
    circuit_breaker: Dict[str, Any] = field(default_factory=lambda: {"max_connections": 100, "http2_max_requests": 100})
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"attempts": 3, "per_try_timeout": "2s", "retry_on": "gateway-error,connect-failure,refused-stream"})


class ServiceMeshManager:
    def __init__(self, config: Optional[ServiceMeshConfig] = None):
        self.config = config or ServiceMeshConfig(service_name="astrovox")
        self._endpoints: Dict[str, List[str]] = {}
        self._traffic_split: Dict[str, float] = {}

    def register_service(self, service_name: str, endpoints: List[str]) -> None:
        self._endpoints[service_name] = endpoints
        logger.info("Registered service %s with %d endpoints", service_name, len(endpoints))

    def set_traffic_split(self, service_name: str, splits: Dict[str, float]) -> None:
        self._traffic_split[service_name] = sum(splits.values())
        logger.info("Set traffic split for %s: %s", service_name, splits)

    def generate_destination_rule(self) -> Dict[str, Any]:
        return {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "DestinationRule",
            "metadata": {"name": self.config.service_name, "namespace": self.config.namespace},
            "spec": {
                "host": self.config.service_name,
                "trafficPolicy": {
                    "connectionPool": {
                        "tcp": {"maxConnections": self.config.circuit_breaker["max_connections"]},
                        "http": {
                            "h1UpgradePolicy": "UPGRADE",
                            "http2MaxRequests": self.config.circuit_breaker["http2_max_requests"],
                        },
                    },
                    "loadBalancer": {"simple": self.config.traffic_policy.value.upper()},
                    "outlierDetection": {
                        "consecutive5xxErrors": self.config.outlier_detection.consecutive_5xx,
                        "interval": self.config.outlier_detection.interval,
                        "baseEjectionTime": self.config.outlier_detection.base_ejection_time,
                    },
                },
            },
        }

    def generate_virtual_service(self, gateway: str = "astrovox-gateway") -> Dict[str, Any]:
        routes = []
        if self._traffic_split:
            weights = {ep: 100 // len(self._endpoints.get(self.config.service_name, [])) for ep in self._endpoints.get(self.config.service_name, [])}
            routes.append({"destination": {"host": self.config.service_name, "port": {"number": self.config.port}}, "weight": weights.get(self.config.service_name, 100)})
        else:
            routes.append({"destination": {"host": self.config.service_name, "port": {"number": self.config.port}}})
        return {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "VirtualService",
            "metadata": {"name": self.config.service_name, "namespace": self.config.namespace},
            "spec": {
                "hosts": [f"{self.config.service_name}.{self.config.namespace}.svc.cluster.local"],
                "gateways": [gateway],
                "http": [
                    {
                        "route": routes,
                        "retries": {
                            "attempts": self.config.retry_policy["attempts"],
                            "perTryTimeout": self.config.retry_policy["per_try_timeout"],
                            "retryOn": self.config.retry_policy["retry_on"],
                        },
                        "timeout": "30s",
                    }
                ],
            },
        }

    def generate_sidecar(self) -> Dict[str, Any]:
        return {
            "apiVersion": "networking.istio.io/v1beta1",
            "kind": "Sidecar",
            "metadata": {"name": f"{self.config.service_name}-sidecar", "namespace": self.config.namespace},
            "spec": {
                "workloadSelector": {"labels": {"app": self.config.service_name}},
                "ingress": [{"port": {"number": self.config.port, "name": "http", "protocol": "HTTP"}}],
                "egress": [{"hosts": ["./*"]}],
            },
        }

    def get_endpoints(self, service_name: str) -> List[str]:
        return self._endpoints.get(service_name, [])
