"""AI Operating System Kernel."""

import hashlib
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"
    TPU = "tpu"


@dataclass
class ModelMetadata:
    name: str
    version: str
    architecture: str
    parameters: int
    dtype: str = "float32"
    tags: list[str] = field(default_factory=list)
    checksum: str | None = None


@dataclass
class DatasetMetadata:
    name: str
    version: str
    format: str
    size_bytes: int
    samples: int | None = None
    tags: list[str] = field(default_factory=list)
    checksum: str | None = None


class ModelManager:
    def __init__(self, registry_path: str = "./models/registry"):
        self.registry_path = registry_path
        self._models: dict[str, ModelMetadata] = {}
        self._loaded: dict[str, Any] = {}

    def register(self, metadata: ModelMetadata) -> None:
        self._models[metadata.name] = metadata
        logger.info("Registered model %s v%s", metadata.name, metadata.version)

    def load(self, name: str, path: str) -> Any:
        if name not in self._models:
            raise KeyError(f"Model {name} not registered")
        if name in self._loaded:
            return self._loaded[name]
        logger.info("Loading model %s from %s", name, path)
        return None

    def unload(self, name: str) -> None:
        self._loaded.pop(name, None)
        logger.info("Unloaded model %s", name)

    def list_models(self) -> list[ModelMetadata]:
        return list(self._models.values())

    def get_metadata(self, name: str) -> ModelMetadata:
        return self._models[name]


class DatasetManager:
    def __init__(self, cache_dir: str = "./data/cache"):
        self.cache_dir = cache_dir
        self._datasets: dict[str, DatasetMetadata] = {}
        os.makedirs(cache_dir, exist_ok=True)

    def register(self, metadata: DatasetMetadata) -> None:
        self._datasets[metadata.name] = metadata
        logger.info("Registered dataset %s v%s", metadata.name, metadata.version)

    def get_path(self, name: str) -> str:
        if name not in self._datasets:
            raise KeyError(f"Dataset {name} not registered")
        return os.path.join(self.cache_dir, name)

    def compute_checksum(self, path: str) -> str:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def list_datasets(self) -> list[DatasetMetadata]:
        return list(self._datasets.values())


class GPUManager:
    def __init__(self) -> None:
        self._allocated: dict[str, int] = {}
        self._total: int = 0
        self._available: int = 0

    def detect_devices(self) -> list[dict[str, Any]]:
        devices = []
        try:
            import torch
            if torch.cuda.is_available():
                for i in range(torch.cuda.device_count()):
                    props = torch.cuda.get_device_properties(i)
                    devices.append({
                        "index": i,
                        "name": props.name,
                        "memory_total_mb": props.total_memory // (1024 * 1024),
                        "type": DeviceType.CUDA.value,
                    })
        except ImportError:
            logger.warning("torch not available for GPU detection")
        if not devices:
            devices.append({"index": 0, "name": "cpu", "memory_total_mb": 0, "type": DeviceType.CPU.value})
        self._total = sum(d["memory_total_mb"] for d in devices)
        self._available = self._total
        return devices

    def allocate(self, owner: str, memory_mb: int) -> bool:
        if memory_mb > self._available:
            return False
        self._allocated[owner] = memory_mb
        self._available -= memory_mb
        logger.info("Allocated %d MB to %s", memory_mb, owner)
        return True

    def release(self, owner: str) -> None:
        if owner in self._allocated:
            self._available += self._allocated.pop(owner)
            logger.info("Released GPU memory for %s", owner)

    def status(self) -> dict[str, Any]:
        return {
            "total_mb": self._total,
            "available_mb": self._available,
            "allocated_mb": self._total - self._available,
            "owners": dict(self._allocated),
        }


class MemoryManager:
    def __init__(self, total_bytes: int = 0) -> None:
        self._total_bytes = total_bytes
        self._used_bytes = 0
        self._blocks: dict[str, int] = {}

    def allocate(self, owner: str, bytes_: int) -> bool:
        if self._used_bytes + bytes_ > self._total_bytes > 0:
            return False
        self._blocks[owner] = bytes_
        self._used_bytes += bytes_
        logger.debug("Allocated %d bytes to %s", bytes_, owner)
        return True

    def release(self, owner: str) -> None:
        if owner in self._blocks:
            self._used_bytes -= self._blocks.pop(owner)

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_bytes": self._total_bytes,
            "used_bytes": self._used_bytes,
            "free_bytes": self._total_bytes - self._used_bytes if self._total_bytes > 0 else None,
            "owners": dict(self._blocks),
        }

    def offload(self, owner: str, target_path: str) -> str:
        if owner not in self._blocks:
            raise KeyError(f"No memory block for {owner}")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            f.write(f"offload:{owner}:{self._blocks[owner]}")
        self.release(owner)
        logger.info("Offloaded %s to %s", owner, target_path)
        return target_path
