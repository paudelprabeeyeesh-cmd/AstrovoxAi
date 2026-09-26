"""Canary and blue-green deployment strategies for inference services."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeploymentVariant(Enum):
    STABLE = "stable"
    CANARY = "canary"
    PREVIEW = "preview"


@dataclass
class CanaryConfig:
    initial_percentage: int = 10
    increment_percentage: int = 20
    max_percentage: int = 100
    interval_seconds: int = 60
    error_threshold: float = 0.05
    latency_threshold_ms: float = 500.0
    min_requests: int = 100


@dataclass
class BlueGreenConfig:
    preview_service: str = "preview"
    active_service: str = "stable"
    auto_promotion: bool = True
    scale_down_delay_seconds: int = 30
    pre_promotion_tests: List[str] = field(default_factory=list)
    post_promotion_tests: List[str] = field(default_factory=list)


class CanaryBlueGreenDeployment:
    def __init__(self, canary_config: Optional[CanaryConfig] = None, blue_green_config: Optional[BlueGreenConfig] = None):
        self.canary_config = canary_config or CanaryConfig()
        self.blue_green_config = blue_green_config or BlueGreenConfig()
        self._variants: Dict[DeploymentVariant, Dict[str, Any]] = {
            DeploymentVariant.STABLE: {"replicas": 3, "version": "stable"},
            DeploymentVariant.CANARY: {"replicas": 1, "version": "canary", "traffic_percentage": 0},
            DeploymentVariant.PREVIEW: {"replicas": 1, "version": "preview", "traffic_percentage": 0},
        }
        self._deployment_history: List[Dict[str, Any]] = []

    def start_canary(self, new_version: str) -> bool:
        logger.info("Starting canary deployment for version %s", new_version)
        self._variants[DeploymentVariant.CANARY]["version"] = new_version
        self._variants[DeploymentVariant.CANARY]["traffic_percentage"] = self.canary_config.initial_percentage
        self._deploy_variant(DeploymentVariant.CANARY, new_version)
        return True

    def promote_canary(self, metrics_fn: Callable[[], Dict[str, float]]) -> bool:
        percentage = self._variants[DeploymentVariant.CANARY]["traffic_percentage"]
        while percentage < self.canary_config.max_percentage:
            logger.info("Canary traffic at %d%%", percentage)
            if not self._evaluate_canary_metrics(metrics_fn):
                logger.warning("Canary metrics failed, rolling back")
                self._rollback_canary()
                return False
            percentage = min(self.canary_config.max_percentage, percentage + self.canary_config.increment_percentage)
            self._variants[DeploymentVariant.CANARY]["traffic_percentage"] = percentage
            self._variants[DeploymentVariant.STABLE]["traffic_percentage"] = 100 - percentage
            time.sleep(self.canary_config.interval_seconds)
        self._promote_to_stable()
        return True

    def _evaluate_canary_metrics(self, metrics_fn: Callable[[], Dict[str, float]]) -> bool:
        metrics = metrics_fn()
        error_rate = metrics.get("error_rate", 0.0)
        latency = metrics.get("latency_p99_ms", 0.0)
        if error_rate > self.canary_config.error_threshold:
            return False
        if latency > self.canary_config.latency_threshold_ms:
            return False
        return True

    def _promote_to_stable(self) -> None:
        canary_version = self._variants[DeploymentVariant.CANARY]["version"]
        self._variants[DeploymentVariant.STABLE]["version"] = canary_version
        self._variants[DeploymentVariant.STABLE]["traffic_percentage"] = 100
        self._variants[DeploymentVariant.CANARY]["traffic_percentage"] = 0
        self._record_deployment("canary", canary_version, "promoted")

    def _rollback_canary(self) -> None:
        self._variants[DeploymentVariant.CANARY]["traffic_percentage"] = 0
        self._variants[DeploymentVariant.STABLE]["traffic_percentage"] = 100
        self._record_deployment("canary", self._variants[DeploymentVariant.CANARY]["version"], "rolled_back")

    def deploy_blue_green(self, new_version: str, deploy_fn: Callable[[str], bool]) -> bool:
        logger.info("Starting blue-green deployment for %s", new_version)
        if not deploy_fn(new_version):
            self._record_deployment("blue_green", new_version, "failed")
            return False
        self._variants[DeploymentVariant.PREVIEW]["version"] = new_version
        self._variants[DeploymentVariant.PREVIEW]["replicas"] = self._variants[DeploymentVariant.STABLE]["replicas"]
        self._record_deployment("blue_green", new_version, "deployed_to_preview")
        return True

    def switch_blue_green(self) -> bool:
        preview = self._variants[DeploymentVariant.PREVIEW]
        stable = self._variants[DeploymentVariant.STABLE]
        stable["version"] = preview["version"]
        stable["replicas"] = preview["replicas"]
        preview["replicas"] = 0
        self._record_deployment("blue_green", stable["version"], "switched")
        return True

    def _deploy_variant(self, variant: DeploymentVariant, version: str) -> None:
        logger.info("Deploying variant %s with version %s", variant.value, version)

    def _record_deployment(self, strategy: str, version: str, status: str) -> None:
        self._deployment_history.append({
            "strategy": strategy,
            "version": version,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_variant_status(self) -> Dict[str, Any]:
        return {
            variant.value: info.copy() for variant, info in self._variants.items()
        }

    def get_deployment_history(self) -> List[Dict[str, Any]]:
        return self._deployment_history.copy()
