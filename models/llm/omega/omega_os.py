"""Omega-1002/1006/1016: AI Operating System for managing models, datasets, GPUs, packages, and security."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    INSTALLED = "installed"
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UPDATING = "updating"


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ModelRecord:
    model_id: str
    version: str
    path: str
    size_bytes: int
    format: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: ComponentStatus = ComponentStatus.INSTALLED
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DatasetRecord:
    dataset_id: str
    version: str
    path: str
    size_bytes: int
    format: str
    splits: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GPUDevice:
    device_id: str
    gpu_type: str
    memory_mb: int
    available_mb: int
    compute_capability: tuple[int, int]
    status: ComponentStatus = ComponentStatus.ACTIVE


@dataclass
class PackageRecord:
    name: str
    version: str
    dependencies: list[str] = field(default_factory=list)
    checksum: str | None = None
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelManager:
    def __init__(self):
        self._models: dict[str, ModelRecord] = {}

    def register(self, model: ModelRecord) -> None:
        self._models[model.model_id] = model
        logger.info("Registered model: %s v%s", model.model_id, model.version)

    def get(self, model_id: str) -> ModelRecord | None:
        return self._models.get(model_id)

    def list_models(self) -> list[ModelRecord]:
        return list(self._models.values())

    def unregister(self, model_id: str) -> None:
        self._models.pop(model_id, None)


class DatasetManager:
    def __init__(self):
        self._datasets: dict[str, DatasetRecord] = {}

    def register(self, dataset: DatasetRecord) -> None:
        self._datasets[dataset.dataset_id] = dataset

    def get(self, dataset_id: str) -> DatasetRecord | None:
        return self._datasets.get(dataset_id)

    def list_datasets(self) -> list[DatasetRecord]:
        return list(self._datasets.values())


class GPUManager:
    def __init__(self):
        self._devices: dict[str, GPUDevice] = {}

    def register_device(self, device: GPUDevice) -> None:
        self._devices[device.device_id] = device

    def get_available(self, min_memory_mb: int = 0, gpu_type: str | None = None) -> list[GPUDevice]:
        devices = []
        for dev in self._devices.values():
            if dev.status != ComponentStatus.ACTIVE:
                continue
            if dev.available_mb < min_memory_mb:
                continue
            if gpu_type and dev.gpu_type != gpu_type:
                continue
            devices.append(dev)
        devices.sort(key=lambda d: d.available_mb, reverse=True)
        return devices

    def allocate(self, device_id: str, memory_mb: int) -> bool:
        dev = self._devices.get(device_id)
        if dev and dev.available_mb >= memory_mb:
            dev.available_mb -= memory_mb
            return True
        return False

    def release(self, device_id: str, memory_mb: int) -> None:
        dev = self._devices.get(device_id)
        if dev:
            dev.available_mb = min(dev.memory_mb, dev.available_mb + memory_mb)


class PackageManager:
    def __init__(self):
        self._packages: dict[str, PackageRecord] = {}

    def install(self, package: PackageRecord) -> None:
        if package.checksum:
            self._verify_checksum(package)
        self._packages[package.name] = package
        logger.info("Installed package: %s v%s", package.name, package.version)

    def uninstall(self, name: str) -> None:
        self._packages.pop(name, None)

    def list_packages(self) -> list[PackageRecord]:
        return list(self._packages.values())

    def _verify_checksum(self, package: PackageRecord) -> None:
        if package.checksum:
            expected = hashlib.sha256(package.name.encode()).hexdigest()[:16]
            if expected != package.checksum:
                raise ValueError(f"Checksum mismatch for {package.name}")


class SecurityManager:
    def __init__(self):
        self._permissions: dict[str, dict[str, Permission]] = {}
        self._audit_log: list[dict[str, Any]] = []

    def grant_permission(self, user_id: str, resource: str, permission: Permission) -> None:
        if user_id not in self._permissions:
            self._permissions[user_id] = {}
        self._permissions[user_id][resource] = permission
        self._audit_log.append({
            "action": "grant",
            "user_id": user_id,
            "resource": resource,
            "permission": permission.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def check_permission(self, user_id: str, resource: str, required: Permission) -> bool:
        perms = self._permissions.get(user_id, {})
        current = perms.get(resource, Permission.READ)
        hierarchy = {Permission.READ: 0, Permission.WRITE: 1, Permission.EXECUTE: 2, Permission.ADMIN: 3}
        return hierarchy.get(current, 0) >= hierarchy.get(required, 0)

    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)


class AIOS:
    def __init__(self):
        self.model_manager = ModelManager()
        self.dataset_manager = DatasetManager()
        self.gpu_manager = GPUManager()
        self.package_manager = PackageManager()
        self.security = SecurityManager()

    def install_model(self, model: ModelRecord) -> None:
        self.model_manager.register(model)

    def allocate_gpu(self, model_id: str, memory_mb: int) -> GPUDevice | None:
        model = self.model_manager.get(model_id)
        gpu_type = model.metadata.get("gpu_type", "any") if model else "any"
        available = self.gpu_manager.get_available(min_memory_mb=memory_mb, gpu_type=gpu_type if gpu_type != "any" else None)
        if available:
            dev = available[0]
            if self.gpu_manager.allocate(dev.device_id, memory_mb):
                return dev
        return None

    def status(self) -> dict[str, Any]:
        return {
            "models": len(self.model_manager.list_models()),
            "datasets": len(self.dataset_manager.list_datasets()),
            "packages": len(self.package_manager.list_packages()),
            "gpus": len(self.gpu_manager._devices),
        }
