"""Plugin-based execution backend registry.

Backends register themselves and can be selected by device, dtype, or
operation kind. The default backend is CPU. Optional GPU backends can be
discovered at runtime when their dependencies are installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Type


@dataclass(frozen=True)
class BackendInfo:
    name: str
    device: str
    supported_dtypes: Tuple[str, ...]
    available: bool


class ExecutionBackend:
    """Interface for an execution backend."""

    info: BackendInfo

    def matmul(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def add(self, left: Any, right: Any) -> Any:
        raise NotImplementedError

    def relu(self, x: Any) -> Any:
        raise NotImplementedError

    def softmax(self, x: Any, dim: int = -1) -> Any:
        raise NotImplementedError


class CPUBackend(ExecutionBackend):
    info = BackendInfo(name="cpu", device="cpu", supported_dtypes=("float32", "float64", "int32", "int64"), available=True)

    def matmul(self, left, right):
        import numpy as np
        return np.matmul(left, right)

    def add(self, left, right):
        import numpy as np
        return np.add(left, right)

    def relu(self, x):
        import numpy as np
        return np.maximum(x, 0)

    def softmax(self, x, dim=-1):
        import numpy as np
        z = x - np.max(x, axis=dim, keepdims=True)
        return np.exp(z) / np.sum(np.exp(z), axis=dim, keepdims=True)


class BackendRegistry:
    _backends: Dict[str, ExecutionBackend] = {}
    _default: Optional[ExecutionBackend] = None

    @classmethod
    def register(cls, backend: ExecutionBackend) -> None:
        cls._backends[backend.info.name] = backend
        if cls._default is None and backend.info.available:
            cls._default = backend

    @classmethod
    def get(cls, name: str) -> ExecutionBackend:
        if name not in cls._backends:
            raise KeyError(f"Unknown backend: {name}")
        return cls._backends[name]

    @classmethod
    def default(cls) -> ExecutionBackend:
        if cls._default is None:
            cls._default = CPUBackend()
        return cls._default

    @classmethod
    def available(cls) -> Iterable[BackendInfo]:
        return (backend.info for backend in cls._backends.values())


BackendRegistry.register(CPUBackend())

try:
    import torch

    class TorchBackend(ExecutionBackend):
        info = BackendInfo(name="torch", device="cuda", supported_dtypes=("float16", "float32", "float64", "bfloat16"), available=torch.cuda.is_available())

        def matmul(self, left, right):
            return torch.matmul(left, right)

        def add(self, left, right):
            return torch.add(left, right)

        def relu(self, x):
            return torch.nn.functional.relu(x)

        def softmax(self, x, dim=-1):
            return torch.nn.functional.softmax(x, dim=dim)

    BackendRegistry.register(TorchBackend())
except ImportError:
    pass
