"""Canary deployments, analysis, and rollback."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CanaryDeployment:
    id: str
    version: str
    traffic_percentage: float
    replicas: int
    healthy: bool = True
    error_rate: float = 0.0
    latency_p99: float = 0.0
    created: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CanaryRegistry:
    def __init__(self) -> None:
        self._deployments: Dict[str, CanaryDeployment] = {}
        self._lock = threading.Lock()

    def register(self, deployment: CanaryDeployment) -> None:
        with self._lock:
            self._deployments[deployment.id] = deployment

    def get(self, deployment_id: str) -> Optional[CanaryDeployment]:
        with self._lock:
            return self._deployments.get(deployment_id)

    def list(self) -> List[CanaryDeployment]:
        with self._lock:
            return list(self._deployments.values())


class CanaryAnalysis:
    def __init__(self) -> None:
        self._deployments = CanaryRegistry()
        self._lock = threading.Lock()

    def deploy(self, version: str, traffic_percentage: float, replicas: int) -> CanaryDeployment:
        deployment = CanaryDeployment(id=f"canary-{int(time.time() * 1000)}", version=version, traffic_percentage=traffic_percentage, replicas=replicas)
        self._deployments.register(deployment)
        logger.info("deployed canary %s at %.2f%% traffic", version, traffic_percentage)
        return deployment

    def promote(self, deployment_id: str) -> Dict[str, Any]:
        deployment = self._deployments.get(deployment_id)
        if deployment is None:
            raise ValueError(f"unknown canary {deployment_id}")
        deployment.traffic_percentage = 100.0
        logger.info("promoted canary %s to production", deployment_id)
        return {"promoted": True, "version": deployment.version}

    def rollback(self, deployment_id: str) -> Dict[str, Any]:
        deployment = self._deployments.get(deployment_id)
        if deployment is None:
            raise ValueError(f"unknown canary {deployment_id}")
        deployment.healthy = False
        deployment.traffic_percentage = 0.0
        logger.info("rolled back canary %s", deployment_id)
        return {"rolled_back": True, "version": deployment.version}

    def analyze(self, deployment_id: str) -> Dict[str, Any]:
        deployment = self._deployments.get(deployment_id)
        if deployment is None:
            raise ValueError(f"unknown canary {deployment_id}")
        healthy = deployment.healthy and deployment.error_rate < 0.1 and deployment.latency_p99 < 500.0
        return {
            "id": deployment_id,
            "healthy": healthy,
            "error_rate": deployment.error_rate,
            "latency_p99": deployment.latency_p99,
            "traffic_percentage": deployment.traffic_percentage,
        }

    def list_deployments(self) -> List[CanaryDeployment]:
        return self._deployments.list()
