"""Zero-downtime deployment strategies for inference services."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class DeploymentStrategy(Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    RECREATE = "recreate"


@dataclass
class DeploymentConfig:
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    max_surge: int = 1
    max_unavailable: int = 0
    progress_deadline_seconds: int = 600
    canary_percentage: int = 10
    canary_interval_seconds: int = 60
    health_check_retries: int = 3
    health_check_timeout: int = 30


class ZeroDowntimeDeployment:
    def __init__(self, config: Optional[DeploymentConfig] = None):
        self.config = config or DeploymentConfig()
        self._deployment_history: List[Dict[str, Any]] = []
        self._current_version: str = "v0"
        self._new_version: Optional[str] = None

    def deploy(self, new_version: str, deploy_fn: Callable[[str], bool], health_check_fn: Callable[[str], bool]) -> bool:
        self._new_version = new_version
        strategy = self.config.strategy
        logger.info("Starting %s deployment to %s", strategy.value, new_version)
        if strategy == DeploymentStrategy.ROLLING:
            return self._rolling_deploy(new_version, deploy_fn, health_check_fn)
        if strategy == DeploymentStrategy.BLUE_GREEN:
            return self._blue_green_deploy(new_version, deploy_fn, health_check_fn)
        if strategy == DeploymentStrategy.CANARY:
            return self._canary_deploy(new_version, deploy_fn, health_check_fn)
        return self._recreate_deploy(new_version, deploy_fn, health_check_fn)

    def _rolling_deploy(self, new_version: str, deploy_fn: Callable[[str], bool], health_check_fn: Callable[[str], bool]) -> bool:
        for i in range(3):
            logger.info("Rolling update step %d/3", i + 1)
            if not deploy_fn(new_version):
                self._rollback()
                return False
            if not self._wait_for_health(health_check_fn):
                self._rollback()
                return False
        self._current_version = new_version
        self._record_deployment("rolling", new_version, "success")
        return True

    def _blue_green_deploy(self, new_version: str, deploy_fn: Callable[[str], bool], health_check_fn: Callable[[str], bool]) -> bool:
        logger.info("Deploying to green environment")
        if not deploy_fn(new_version):
            self._record_deployment("blue_green", new_version, "failed")
            return False
        if not self._wait_for_health(health_check_fn):
            self._record_deployment("blue_green", new_version, "failed")
            return False
        logger.info("Switching traffic to green")
        self._switch_traffic("green")
        self._current_version = new_version
        self._record_deployment("blue_green", new_version, "success")
        return True

    def _canary_deploy(self, new_version: str, deploy_fn: Callable[[str], bool], health_check_fn: Callable[[str], bool]) -> bool:
        percentage = self.config.canary_percentage
        for _ in range(3):
            logger.info("Canary deployment at %d%%", percentage)
            if not deploy_fn(new_version):
                self._rollback()
                return False
            if not self._wait_for_health(health_check_fn):
                self._rollback()
                return False
            percentage = min(100, percentage * 2)
        self._switch_traffic("new")
        self._current_version = new_version
        self._record_deployment("canary", new_version, "success")
        return True

    def _recreate_deploy(self, new_version: str, deploy_fn: Callable[[str], bool], health_check_fn: Callable[[str], bool]) -> bool:
        logger.info("Recreate deployment")
        self._drain_traffic()
        if not deploy_fn(new_version):
            self._restore_traffic()
            return False
        if not self._wait_for_health(health_check_fn):
            self._rollback()
            return False
        self._restore_traffic()
        self._current_version = new_version
        self._record_deployment("recreate", new_version, "success")
        return True

    def _wait_for_health(self, health_check_fn: Callable[[str], bool]) -> bool:
        for _ in range(self.config.health_check_retries):
            if health_check_fn(self._new_version or self._current_version):
                return True
            time.sleep(self.config.health_check_timeout)
        return False

    def _rollback(self) -> None:
        logger.warning("Rolling back to %s", self._current_version)
        self._record_deployment(self.config.strategy.value, self._current_version, "rolled_back")

    def _switch_traffic(self, target: str) -> None:
        logger.info("Switching traffic to %s", target)

    def _drain_traffic(self) -> None:
        logger.info("Draining traffic")

    def _restore_traffic(self) -> None:
        logger.info("Restoring traffic")

    def _record_deployment(self, strategy: str, version: str, status: str) -> None:
        self._deployment_history.append({
            "strategy": strategy,
            "version": version,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_deployment_history(self) -> List[Dict[str, Any]]:
        return self._deployment_history.copy()
