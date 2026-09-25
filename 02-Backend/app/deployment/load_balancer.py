from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter, DeploymentConfig


class LBAlgorithm(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    WEIGHTED = "weighted"


class HealthCheckType(Enum):
    HTTP = "http"
    HTTPS = "https"
    TCP = "tcp"
    GRPC = "grpc"


@dataclass
class HealthCheckConfig:
    protocol: HealthCheckType
    path: str = "/health"
    port: int = 80
    interval_seconds: int = 30
    timeout_seconds: int = 5
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3


@dataclass
class LoadBalancerConfig:
    name: str
    algorithm: LBAlgorithm = LBAlgorithm.ROUND_ROBIN
    listeners: List[Dict[str, Any]] = None
    health_check: Optional[HealthCheckConfig] = None
    cross_zone: bool = True

    def __post_init__(self):
        if self.listeners is None:
            self.listeners = [{"port": 80, "protocol": "HTTP"}]


class GlobalLoadBalancer:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.load_balancers: Dict[str, LoadBalancerConfig] = {}

    def create_load_balancer(self, config: LoadBalancerConfig) -> Dict[str, Any]:
        self.load_balancers[config.name] = config
        listeners = [{"port": l["port"], "protocol": l["protocol"]} for l in config.listeners]
        return self.adapter.configure_load_balancer(config.name, listeners)

    def update_algorithm(self, lb_name: str, algorithm: LBAlgorithm) -> Dict[str, Any]:
        if lb_name not in self.load_balancers:
            raise ValueError(f"Load balancer {lb_name} not found")
        self.load_balancers[lb_name].algorithm = algorithm
        return {
            "status": "updated",
            "lb_name": lb_name,
            "algorithm": algorithm.value,
        }

    def register_targets(self, lb_name: str, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        if lb_name not in self.load_balancers:
            raise ValueError(f"Load balancer {lb_name} not found")
        return {
            "status": "registered",
            "lb_name": lb_name,
            "target_count": len(targets),
        }

    def get_status(self, lb_name: str) -> Dict[str, Any]:
        if lb_name not in self.load_balancers:
            raise ValueError(f"Load balancer {lb_name} not found")
        config = self.load_balancers[lb_name]
        return {
            "name": lb_name,
            "algorithm": config.algorithm.value,
            "listeners": config.listeners,
            "cross_zone": config.cross_zone,
        }
