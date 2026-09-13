"""ACDOS Model Serving Platform: model registry, version management, A/B testing,
canary deployments, dynamic routing, auto-scaling, request batching, streaming.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from . import make_id, now, now_iso
from .control_plane import ClusterCoordinator, get_cluster_coordinator
from ..logging_config import get_logger

logger = get_logger(__name__)


class ModelStatus(str, Enum):
    REGISTERED = "registered"
    LOADING = "loading"
    READY = "ready"
    DEGRADED = "degraded"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class DeploymentStrategy(str, Enum):
    RECREATE = "recreate"
    ROLLING = "rolling"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"


@dataclass
class ModelVersion:
    id: str
    model_id: str
    version: str
    artifact_uri: str
    framework: str  # "pytorch", "tensorflow", "onnx", "gguf", "custom"
    config: Dict[str, Any] = field(default_factory=dict)
    requirements: Dict[str, float] = field(default_factory=dict)  # cpu, gpu, memory
    status: ModelStatus = ModelStatus.REGISTERED
    created_at: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "version": self.version,
            "artifact_uri": self.artifact_uri,
            "framework": self.framework,
            "config": self.config,
            "requirements": self.requirements,
            "status": self.status.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class Model:
    id: str
    name: str
    owner: str
    description: str = ""
    versions: Dict[str, ModelVersion] = field(default_factory=dict)
    current_version: Optional[str] = None
    default_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "owner": self.owner,
            "description": self.description,
            "versions": {k: v.to_dict() for k, v in self.versions.items()},
            "current_version": self.current_version,
            "default_version": self.default_version,
            "tags": self.tags,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class ModelRegistry:
    def __init__(self) -> None:
        self._models: Dict[str, Model] = {}
        self._lock = threading.Lock()

    def register(self, model: Model) -> Model:
        with self._lock:
            if model.id in self._models:
                raise ValueError(f"Model {model.id} already exists")
            self._models[model.id] = model
            return model

    def get(self, model_id: str) -> Optional[Model]:
        with self._lock:
            return self._models.get(model_id)

    def delete(self, model_id: str) -> Optional[Model]:
        with self._lock:
            return self._models.pop(model_id, None)

    def list(self, owner: Optional[str] = None) -> List[Model]:
        with self._lock:
            items = list(self._models.values())
            if owner:
                items = [m for m in items if m.owner == owner]
            return items

    def add_version(self, model_id: str, version: ModelVersion) -> ModelVersion:
        with self._lock:
            model = self._models.get(model_id)
            if not model:
                raise ValueError(f"Model {model_id} not found")
            if version.version in model.versions:
                raise ValueError(f"Version {version.version} already exists")
            model.versions[version.version] = version
            if model.default_version is None:
                model.default_version = version.version
            if model.current_version is None:
                model.current_version = version.version
            return version

    def set_current(self, model_id: str, version: str) -> bool:
        with self._lock:
            model = self._models.get(model_id)
            if not model or version not in model.versions:
                return False
            model.current_version = version
            return True

    def set_default(self, model_id: str, version: str) -> bool:
        with self._lock:
            model = self._models.get(model_id)
            if not model or version not in model.versions:
                return False
            model.default_version = version
            return True


class Deployment:
    def __init__(
        self,
        id: str,
        model_id: str,
        version: str,
        strategy: DeploymentStrategy = DeploymentStrategy.ROLLING,
        replicas: int = 1,
        canary_percentage: float = 0.0,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = id
        self.model_id = model_id
        self.version = version
        self.strategy = strategy
        self.replicas = replicas
        self.canary_percentage = canary_percentage
        self.config = config or {}
        self.status: str = "pending"
        self.replicas_ready: int = 0
        self.created_at = now()
        self.updated_at = now()
        self.health_checks: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_id": self.model_id,
            "version": self.version,
            "strategy": self.strategy.value,
            "replicas": self.replicas,
            "canary_percentage": self.canary_percentage,
            "config": self.config,
            "status": self.status,
            "replicas_ready": self.replicas_ready,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class DeploymentManager:
    def __init__(self, registry: ModelRegistry, coordinator: ClusterCoordinator) -> None:
        self.registry = registry
        self.coordinator = coordinator
        self._deployments: Dict[str, Deployment] = {}
        self._lock = threading.Lock()

    def create(self, deployment: Deployment) -> Deployment:
        with self._lock:
            if deployment.id in self._deployments:
                raise ValueError(f"Deployment {deployment.id} already exists")
            self._deployments[deployment.id] = deployment
            return deployment

    def get(self, deployment_id: str) -> Optional[Deployment]:
        with self._lock:
            return self._deployments.get(deployment_id)

    def list(self, model_id: Optional[str] = None) -> List[Deployment]:
        with self._lock:
            items = list(self._deployments.values())
            if model_id:
                items = [d for d in items if d.model_id == model_id]
            return items

    def delete(self, deployment_id: str) -> Optional[Deployment]:
        with self._lock:
            return self._deployments.pop(deployment_id, None)

    async def rollout(self, deployment_id: str) -> Dict[str, Any]:
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        deployment.status = "rolling_out"
        deployment.updated_at = now()

        # Simulate rollout based on strategy
        if deployment.strategy == DeploymentStrategy.RECREATE:
            return await self._rollout_recreate(deployment)
        elif deployment.strategy == DeploymentStrategy.ROLLING:
            return await self._rollout_rolling(deployment)
        elif deployment.strategy == DeploymentStrategy.CANARY:
            return await self._rollout_canary(deployment)
        elif deployment.strategy == DeploymentStrategy.BLUE_GREEN:
            return await self._rollout_blue_green(deployment)
        return {"ok": False, "error": "unknown strategy"}

    async def _rollout_recreate(self, deployment: Deployment) -> Dict[str, Any]:
        # Stop all old, start new
        await asyncio.sleep(0.1)  # simulate
        deployment.status = "active"
        deployment.replicas_ready = deployment.replicas
        deployment.updated_at = now()
        return {"ok": True, "strategy": "recreate"}

    async def _rollout_rolling(self, deployment: Deployment) -> Dict[str, Any]:
        # Replace one by one
        for i in range(deployment.replicas):
            await asyncio.sleep(0.05)
            deployment.replicas_ready = i + 1
            deployment.updated_at = now()
        deployment.status = "active"
        return {"ok": True, "strategy": "rolling"}

    async def _rollout_canary(self, deployment: Deployment) -> Dict[str, Any]:
        # Deploy canary percentage, then promote
        canary_replicas = max(1, int(deployment.replicas * deployment.canary_percentage))
        for i in range(canary_replicas):
            await asyncio.sleep(0.05)
        deployment.replicas_ready = canary_replicas
        deployment.updated_at = now()
        # Simulate canary promotion
        await asyncio.sleep(0.1)
        deployment.replicas_ready = deployment.replicas
        deployment.status = "active"
        return {"ok": True, "strategy": "canary", "canary_replicas": canary_replicas}

    async def _rollout_blue_green(self, deployment: Deployment) -> Dict[str, Any]:
        # Deploy to green, then switch
        await asyncio.sleep(0.1)
        deployment.status = "active"
        deployment.replicas_ready = deployment.replicas
        deployment.updated_at = now()
        return {"ok": True, "strategy": "blue_green"}

    def scale(self, deployment_id: str, replicas: int) -> bool:
        with self._lock:
            deployment = self._deployments.get(deployment_id)
            if not deployment:
                return False
            deployment.replicas = replicas
            deployment.updated_at = now()
            return True

    def pause(self, deployment_id: str) -> bool:
        with self._lock:
            deployment = self._deployments.get(deployment_id)
            if not deployment:
                return False
            deployment.status = "paused"
            deployment.updated_at = now()
            return True

    def resume(self, deployment_id: str) -> bool:
        with self._lock:
            deployment = self._deployments.get(deployment_id)
            if not deployment:
                return False
            deployment.status = "active"
            deployment.updated_at = now()
            return True

    def status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            deployment = self._deployments.get(deployment_id)
            return deployment.to_dict() if deployment else None


class ModelServer:
    """High-level model serving interface with dynamic routing, batching, A/B testing."""

    def __init__(
        self,
        registry: ModelRegistry,
        deployment_manager: DeploymentManager,
        coordinator: ClusterCoordinator,
    ) -> None:
        self.registry = registry
        self.deployments = deployment_manager
        self.coordinator = coordinator
        self._ab_tests: Dict[str, Dict[str, Any]] = {}
        self._batch_queue: asyncio.Queue = asyncio.Queue()
        self._batching_task: Optional[asyncio.Task] = None
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def predict(
        self,
        model_id: str,
        inputs: List[Any],
        *,
        version: Optional[str] = None,
        ab_test: Optional[str] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        model = self.registry.get(model_id)
        if not model:
            return {"error": "model not found", "status": 404}

        version = version or model.current_version or model.default_version
        if not version or version not in model.versions:
            return {"error": "no version available", "status": 404}

        # A/B test routing
        if ab_test and ab_test in self._ab_tests:
            test = self._ab_tests[ab_test]
            variant = self._route_ab_test(test, model_id)
            version = variant

        # Simulate inference
        start = time.time()
        outputs = [f"output_for_{i}" for i in range(len(inputs))]
        latency = time.time() - start

        return {
            "model_id": model_id,
            "version": version,
            "outputs": outputs,
            "latency_ms": round((time.time() - start) * 1000, 2),
        }

    def _route_ab_test(self, test: Dict[str, Any], model_id: str) -> str:
        variants = test.get("variants", {})
        weights = [v.get("weight", 1) for v in variants.values()]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0
        for variant, weight in zip(variants.keys(), weights):
            cumulative += weight
            if r <= cumulative:
                return variant
        return model.current_version or model.default_version or ""

    def create_ab_test(
        self,
        name: str,
        variants: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        test = {
            "name": name,
            "variants": variants,
            "created_at": now(),
        }
        self._ab_tests[name] = test
        return test

    async def start_batching(self, batch_size: int = 8, max_wait_ms: float = 10.0) -> None:
        if self._batching_task is not None:
            return

        async def batch_worker():
            while True:
                batch = []
                try:
                    item = await asyncio.wait_for(self._batch_queue.get(), timeout=max_wait_ms / 1000)
                    batch.append(item)
                    while len(batch) < batch_size:
                        try:
                            item = self._batch_queue.get_nowait()
                            batch.append(item)
                        except asyncio.QueueEmpty:
                            break
                    # Process batch
                    for item in batch:
                        item["result"] = {"batched": True, "items": len(batch)}
                except asyncio.CancelledError:
                    break

        self._batching_task = asyncio.create_task(batch_worker())

    async def stop_batching(self) -> None:
        if self._batching_task:
            self._batching_task.cancel()
            try:
                await self._batching_task
            except asyncio.CancelledError:
                pass
            self._batching_task = None


import random  # noqa: E402
import threading  # noqa: E402


# ---------------------------------------------------------------------------
# Global
# ---------------------------------------------------------------------------

_GLOBAL_REGISTRY: Optional[ModelRegistry] = None
_GLOBAL_DEPLOYMENTS: Optional[DeploymentManager] = None
_GLOBAL_SERVER: Optional[ModelServer] = None


def get_model_registry() -> ModelRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ModelRegistry()
    return _GLOBAL_REGISTRY


def get_deployment_manager() -> DeploymentManager:
    global _GLOBAL_DEPLOYMENTS
    if _GLOBAL_DEPLOYMENTS is None:
        _GLOBAL_DEPLOYMENTS = DeploymentManager(get_model_registry(), get_cluster_coordinator())
    return _GLOBAL_DEPLOYMENTS


def get_model_server() -> ModelServer:
    global _GLOBAL_SERVER
    if _GLOBAL_SERVER is None:
        _GLOBAL_SERVER = ModelServer(
            get_model_registry(),
            get_deployment_manager(),
            get_cluster_coordinator(),
        )
    return _GLOBAL_SERVER