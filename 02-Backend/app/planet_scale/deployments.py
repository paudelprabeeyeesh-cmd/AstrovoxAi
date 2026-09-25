"""Deployment automation: blue/green, canary, automatic rollback, self-healing."""
from __future__ import annotations

import logging
import os
import time
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DeploymentResult:
    strategy: str
    success: bool
    previous_version: str | None = None
    current_version: str | None = None
    error: str | None = None


class BlueGreenDeployer:
    def __init__(self, service: str, blue: str, green: str) -> None:
        self.service = service
        self.blue = blue
        self.green = green
        self.active = blue

    def deploy(self, image: str) -> DeploymentResult:
        target = self.blue if self.active == self.green else self.green
        try:
            self._apply(target, image)
            self._wait_healthy(target)
            self._switch_traffic(target)
            previous = self.active
            self.active = target
            return DeploymentResult(strategy="blue_green", success=True, previous_version=previous, current_version=target)
        except Exception as exc:
            return DeploymentResult(strategy="blue_green", success=False, error=str(exc))

    def rollback(self) -> DeploymentResult:
        target = self.blue if self.active == self.green else self.green
        try:
            self._switch_traffic(target)
            previous = self.active
            self.active = target
            return DeploymentResult(strategy="blue_green", success=True, previous_version=previous, current_version=target)
        except Exception as exc:
            return DeploymentResult(strategy="blue_green", success=False, error=str(exc))

    def _apply(self, target: str, image: str) -> None:
        logger.info("Applying %s with image %s", target, image)

    def _wait_healthy(self, target: str, timeout: int = 120) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._is_healthy(target):
                return
            time.sleep(5)
        raise RuntimeError(f"{target} did not become healthy in time")

    def _is_healthy(self, target: str) -> bool:
        return True

    def _switch_traffic(self, target: str) -> None:
        logger.info("Switching traffic to %s", target)


class CanaryDeployer:
    def __init__(self, service: str, stages: list[dict]) -> None:
        self.service = service
        self.stages = stages

    def deploy(self, image: str) -> DeploymentResult:
        try:
            for stage in self.stages:
                self._apply(stage["percentage"], image)
                self._observe(stage["duration_minutes"])
            return DeploymentResult(strategy="canary", success=True, current_version=image)
        except Exception as exc:
            return DeploymentResult(strategy="canary", success=False, error=str(exc))

    def _apply(self, percentage: int, image: str) -> None:
        logger.info("Routing %s%% traffic to %s", percentage, image)

    def _observe(self, duration_minutes: int) -> None:
        logger.info("Observing canary for %sm", duration_minutes)


class SelfHealingDeployer:
    def __init__(self, deployer: Any) -> None:
        self.deployer = deployer

    def deploy(self, image: str) -> DeploymentResult:
        result = self.deployer.deploy(image)
        if not result.success:
            rollback = self.deployer.rollback()
            return DeploymentResult(strategy="self_healing", success=rollback.success, previous_version=result.previous_version, current_version=rollback.current_version, error=rollback.error or result.error)
        return result
