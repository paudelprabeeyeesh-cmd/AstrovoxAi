from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional


class KernelType(str, Enum):
    MATRIX_MULTIPLY = "matrix_multiply"
    VECTOR_ADD = "vector_add"
    ACTIVATION = "activation"
    NORMALIZATION = "normalization"


@dataclass
class Kernel:
    kernel_id: str
    kernel_type: KernelType
    cost: float
    supported_devices: List[str]

    def can_run_on(self, device_id: str) -> bool:
        return device_id in self.supported_devices


@dataclass
class DispatchResult:
    kernel_id: str
    device_id: str
    success: bool
    message: str = ""


class KernelDispatcher:
    def __init__(self) -> None:
        self._kernels: Dict[str, Kernel] = {}
        self._device_capabilities: Dict[str, List[KernelType]] = {}
        self._dispatch_log: List[DispatchResult] = []

    def register_kernel(self, kernel: Kernel) -> None:
        self._kernels[kernel.kernel_id] = kernel

    def register_device(self, device_id: str, capabilities: List[KernelType]) -> None:
        self._device_capabilities[device_id] = capabilities

    def dispatch(self, kernel_id: str, device_id: str) -> DispatchResult:
        if kernel_id not in self._kernels:
            result = DispatchResult(kernel_id=kernel_id, device_id=device_id, success=False, message="unknown kernel")
            self._dispatch_log.append(result)
            return result
        if device_id not in self._device_capabilities:
            result = DispatchResult(kernel_id=kernel_id, device_id=device_id, success=False, message="unknown device")
            self._dispatch_log.append(result)
            return result
        kernel = self._kernels[kernel_id]
        if not kernel.can_run_on(device_id):
            result = DispatchResult(kernel_id=kernel_id, device_id=device_id, success=False, message="incompatible device")
            self._dispatch_log.append(result)
            return result
        device_caps = self._device_capabilities[device_id]
        if kernel.kernel_type not in device_caps:
            result = DispatchResult(kernel_id=kernel_id, device_id=device_id, success=False, message="capability mismatch")
            self._dispatch_log.append(result)
            return result
        result = DispatchResult(kernel_id=kernel_id, device_id=device_id, success=True, message="dispatched")
        self._dispatch_log.append(result)
        return result

    def find_best_device(self, kernel_id: str) -> Optional[str]:
        if kernel_id not in self._kernels:
            return None
        kernel = self._kernels[kernel_id]
        candidates = [did for did, caps in self._device_capabilities.items() if kernel.kernel_type in caps and kernel.can_run_on(did)]
        if not candidates:
            return None
        return min(candidates)

    def dispatch_log(self) -> List[DispatchResult]:
        return list(self._dispatch_log)

    def clear_log(self) -> None:
        self._dispatch_log.clear()
