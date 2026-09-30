"""Device abstraction for the Astrovox tensor engine.

A :class:`Device` is a value object describing *where* a buffer lives. The
engine dispatches computation through backends registered against a device
type, so adding an accelerator means registering a backend rather than editing
kernels.
"""

from __future__ import annotations

import platform
from dataclasses import dataclass
from enum import Enum
from typing import Any


class DeviceType(str, Enum):
    """The kind of hardware a device refers to."""

    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    MPS = "mps"
    TPU = "tpu"


@dataclass(frozen=True)
class Device:
    """A compute device identified by type and optional ordinal.

    Attributes:
        device_type: the hardware family.
        index: ordinal within that family; ``0`` for CPU.
    """

    device_type: DeviceType = DeviceType.CPU
    index: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.device_type, DeviceType):
            object.__setattr__(self, "device_type", DeviceType(self.device_type))
        if self.index < 0:
            raise ValueError(f"Device index must be non-negative, got {self.index}")

    @property
    def is_cpu(self) -> bool:
        """True when this device is the host CPU."""
        return self.device_type is DeviceType.CPU

    def __str__(self) -> str:
        if self.is_cpu:
            return "cpu"
        return f"{self.device_type.value}:{self.index}"

    @classmethod
    def parse(cls, spec: str | Device) -> Device:
        """Parse ``"cpu"``, ``"cuda:1"`` or an existing :class:`Device`."""
        if isinstance(spec, Device):
            return spec
        text = str(spec).strip().lower()
        if not text:
            raise ValueError("Cannot parse an empty device string")
        if ":" in text:
            type_text, _, index_text = text.partition(":")
            return cls(DeviceType(type_text), int(index_text))
        return cls(DeviceType(text), 0)


CPU = Device(DeviceType.CPU, 0)


class Capability(str, Enum):
    """Optional device features the compiler may target."""

    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"
    TENSOR_CORES = "tensor_cores"
    UNIFIED_MEMORY = "unified_memory"
    ASYNC_EXECUTION = "async_execution"


class Backend:
    """Interface a device backend must implement to execute kernels.

    Backends own the actual buffers for their device. The engine only ever
    calls :meth:`dispatch`, which lets a backend fuse, reorder, or offload a
    single operation.
    """

    device_type: DeviceType = DeviceType.CPU

    def supports(self, capability: Capability) -> bool:
        """Return whether this backend provides ``capability``."""
        return False

    def dispatch(self, op: str, inputs: list[Any], **kwargs: Any) -> Any:
        """Execute ``op`` over ``inputs`` and return the result buffer."""
        raise NotImplementedError(f"{type(self).__name__} does not implement dispatch()")

    def synchronize(self) -> None:
        """Block until all queued work on this backend has completed."""

    def allocate(self, shape: tuple[int, ...], dtype: Any) -> Any:
        """Allocate an uninitialized buffer for ``shape`` and ``dtype``."""
        raise NotImplementedError

    def free(self, buffer: Any) -> None:
        """Release ``buffer`` back to the backend's pool."""

    def memory_used(self) -> int:
        """Return bytes currently held by this backend."""
        return 0


_REGISTRY: dict[DeviceType, Backend] = {}


def register_backend(backend: Backend, override: bool = False) -> Backend:
    """Register ``backend`` as the executor for its device type."""
    key = backend.device_type
    if key in _REGISTRY and not override:
        raise RuntimeError(f"A backend for {key} is already registered")
    _REGISTRY[key] = backend
    return backend


def get_backend(device: Device) -> Backend:
    """Return the backend responsible for ``device``.

    Falls back to the CPU backend for unregistered accelerator types so that a
    program written for CUDA still runs on a machine without it.
    """
    backend = _REGISTRY.get(device.device_type)
    if backend is None:
        backend = _REGISTRY[DeviceType.CPU]
    return backend


def available_device_types() -> list[DeviceType]:
    """Return every device type with a registered backend."""
    return sorted(_REGISTRY, key=lambda d: d.value)


def default_device() -> Device:
    """Return the best device available on this machine."""
    for candidate in (DeviceType.CUDA, DeviceType.ROCM, DeviceType.MPS):
        if candidate in _REGISTRY:
            return Device(candidate, 0)
    return CPU


def describe_environment() -> dict[str, Any]:
    """Return a snapshot of host and accelerator information for provenance."""
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "available_device_types": [d.value for d in available_device_types()],
    }
    for device_type in (DeviceType.CUDA, DeviceType.ROCM, DeviceType.MPS):
        backend = _REGISTRY.get(device_type)
        if backend is not None:
            info[device_type.value] = {"memory_used_bytes": backend.memory_used()}
    return info
