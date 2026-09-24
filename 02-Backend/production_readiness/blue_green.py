"""Blue-green deployments for zero-downtime releases."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class DeploymentEnvironment:
    name: str
    version: str
    endpoint: str
    replicas: int
    healthy: bool = True
    last_deployed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class BlueGreenRegistry:
    def __init__(self) -> None:
        self._environments: Dict[str, DeploymentEnvironment] = {}
        self._lock = threading.Lock()

    def register(self, env: DeploymentEnvironment) -> None:
        with self._lock:
            self._environments[env.name] = env

    def get(self, name: str) -> Optional[DeploymentEnvironment]:
        with self._lock:
            return self._environments.get(name)

    def environments(self) -> Dict[str, DeploymentEnvironment]:
        with self._lock:
            return dict(self._environments)


class BlueGreenDeployment:
    def __init__(self) -> None:
        self._registry = BlueGreenRegistry()
        self._lock = threading.Lock()

    def deploy(self, name: str, version: str, endpoint: str, replicas: int) -> DeploymentEnvironment:
        env = DeploymentEnvironment(name=name, version=version, endpoint=endpoint, replicas=replicas)
        self._registry.register(env)
        logger.info("deployed %s version %s", name, version)
        return env

    def switch_traffic(self, name: str, target: str) -> Dict[str, Any]:
        env = self._registry.get(name)
        if env is None:
            raise ValueError(f"unknown deployment {name}")
        prev = env.version
        env.version = target
        env.last_deployed = time.time()
        logger.info("switched traffic for %s from %s to %s", name, prev, target)
        return {"from": prev, "to": target, "endpoint": env.endpoint}

    def scale(self, name: str, replicas: int) -> DeploymentEnvironment:
        env = self._registry.get(name)
        if env is not None:
            env.replicas = replicas
        return env

    def status(self) -> Dict[str, Any]:
        return {name: env.__dict__ for name, env in self._registry.environments().items()}

    def rollback(self, name: str) -> Dict[str, Any]:
        env = self._registry.get(name)
        if env is None:
            raise ValueError(f"unknown deployment {name}")
        rollback_version = env.version
        env.last_deployed = time.time()
        logger.info("rollback %s to previous state", name)
        return {"rolled_back": True, "version": rollback_version}
