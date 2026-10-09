from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from heapq import heappush, heappop
from typing import Any, Callable, Dict, List, Optional


class DeviceType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"


class DeviceStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


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
        self.status = DeviceStatus.IDLE
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

    def get_info(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "status": self.status.value,
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


@dataclass(order=True)
class QueuedTask:
    priority: int
    device_type: DeviceType = field(compare=False)
    size: int = field(compare=False)
    task_id: str = field(compare=False)
    callback: Optional[Callable[[str], None]] = field(default=None, compare=False)


class DeviceManager:
    def __init__(self) -> None:
        self.devices: List[AbstractDevice] = []
        self._device_by_id: Dict[str, AbstractDevice] = {}
        self._queue: List[QueuedTask] = []

    def register_device(self, device: AbstractDevice) -> None:
        self.devices.append(device)
        self._device_by_id[device.device_id] = device

    def get_device(self, device_id: str) -> Optional[AbstractDevice]:
        return self._device_by_id.get(device_id)

    def get_devices_by_type(self, device_type: DeviceType) -> List[AbstractDevice]:
        return [d for d in self.devices if d.device_type == device_type]

    def best_device_for(self, size: int) -> Optional[AbstractDevice]:
        candidates = [d for d in self.devices if d.memory.free >= size and d.status == DeviceStatus.IDLE]
        if not candidates:
            return None
        return min(candidates, key=lambda d: d.latency_ms)

    def submit_task(self, task_id: str, device_type: DeviceType, size: int, priority: int = 0) -> Optional[str]:
        task = QueuedTask(priority=-priority, device_type=device_type, size=size, task_id=task_id)
        heappush(self._queue, task)
        device = self.best_device_for(size)
        if device and device.device_type == device_type:
            return device.device_id
        return None

    def process_queue(self) -> List[str]:
        results = []
        while self._queue:
            task = heappop(self._queue)
            device = self.best_device_for(task.size)
            if device:
                device.status = DeviceStatus.BUSY
                results.append(device.device_id)
        return results

    def release_device(self, device_id: str) -> None:
        device = self.get_device(device_id)
        if device:
            device.status = DeviceStatus.IDLE

    def summary(self) -> List[dict]:
        return [d.get_info() for d in self.devices]
