from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class DeviceType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"


@dataclass
class DeviceMemory:
    total: int
    used: int = 0

    @property
    def free(self) -> int:
        return self.total - self.used

    def allocate(self, size: int) -> bool:
        if size <= 0 or size > self.free:
            return False
        self.used += size
        return True

    def free_block(self, size: int) -> None:
        self.used = max(0, self.used - size)


class AbstractDevice(ABC):
    def __init__(self, device_id: str, device_type: DeviceType, memory: DeviceMemory) -> None:
        self.device_id = device_id
        self.device_type = device_type
        self.memory = memory
        self.latency_ms = self._base_latency()

    @abstractmethod
    def _base_latency(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def allocate_tensor(self, size: int) -> Optional[int]:
        raise NotImplementedError

    @abstractmethod
    def free_tensor(self, pointer: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def transfer_to(self, data: List[float], pointer: int) -> List[float]:
        raise NotImplementedError

    def get_info(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "total_memory": self.memory.total,
            "used_memory": self.memory.used,
            "free_memory": self.memory.free,
            "latency_ms": self.latency_ms,
        }


class CPUDevice(AbstractDevice):
    def __init__(self, device_id: str, memory: DeviceMemory) -> None:
        super().__init__(device_id, DeviceType.CPU, memory)

    def _base_latency(self) -> float:
        return 1.0

    def allocate_tensor(self, size: int) -> Optional[int]:
        if self.memory.allocate(size):
            return size
        return None

    def free_tensor(self, pointer: int) -> None:
        self.memory.free_block(pointer)

    def transfer_to(self, data: List[float], pointer: int) -> List[float]:
        return data


class GPUDevice(AbstractDevice):
    def __init__(self, device_id: str, memory: DeviceMemory) -> None:
        super().__init__(device_id, DeviceType.GPU, memory)

    def _base_latency(self) -> float:
        return 0.2

    def allocate_tensor(self, size: int) -> Optional[int]:
        if self.memory.allocate(size):
            return size * 2
        return None

    def free_tensor(self, pointer: int) -> None:
        self.memory.free_block(pointer // 2)

    def transfer_to(self, data: List[float], pointer: int) -> List[float]:
        return data


class TPUDevice(AbstractDevice):
    def __init__(self, device_id: str, memory: DeviceMemory) -> None:
        super().__init__(device_id, DeviceType.TPU, memory)

    def _base_latency(self) -> float:
        return 0.1

    def allocate_tensor(self, size: int) -> Optional[int]:
        if self.memory.allocate(size):
            return size * 4
        return None

    def free_tensor(self, pointer: int) -> None:
        self.memory.free_block(pointer // 4)

    def transfer_to(self, data: List[float], pointer: int) -> List[float]:
        return data


class DeviceManager:
    def __init__(self) -> None:
        self.devices: List[AbstractDevice] = []

    def register_device(self, device: AbstractDevice) -> None:
        self.devices.append(device)

    def get_device(self, device_id: str) -> Optional[AbstractDevice]:
        for device in self.devices:
            if device.device_id == device_id:
                return device
        return None

    def get_devices_by_type(self, device_type: DeviceType) -> List[AbstractDevice]:
        return [d for d in self.devices if d.device_type == device_type]

    def best_device_for(self, size: int) -> Optional[AbstractDevice]:
        candidates = [d for d in self.devices if d.memory.free >= size]
        if not candidates:
            return None
        return min(candidates, key=lambda d: d.latency_ms)

    def summary(self) -> List[dict]:
        return [d.get_info() for d in self.devices]
