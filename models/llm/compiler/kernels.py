from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KernelSpec:
    name: str
    backend: str
    ops: List[str]
    tile_size: int = 1
    preferred_dtypes: List[str] = field(default_factory=list)
    attrs: Dict[str, Any] = field(default_factory=dict)


class KernelRegistry:
    def __init__(self) -> None:
        self._kernels: List[KernelSpec] = []

    def register(self, kernel: KernelSpec) -> None:
        self._kernels.append(kernel)

    def query(self, op: str, backend: Optional[str] = None) -> List[KernelSpec]:
        return [k for k in self._kernels if op in k.ops and (backend is None or k.backend == backend)]

    def all(self) -> List[KernelSpec]:
        return list(self._kernels)


class PerformanceModel:
    def predict(self, kernel: KernelSpec, batch_size: int, seq_len: int, hidden_dim: int) -> float:
        base = 1.0
        if kernel.backend == "cuda":
            base *= 0.5
        elif kernel.backend == "triton":
            base *= 0.7
        scale = (batch_size * seq_len * hidden_dim) / (kernel.tile_size * 1024)
        return base * max(scale, 0.1)


class AutoTuner:
    def __init__(self, registry: KernelRegistry, perf_model: PerformanceModel) -> None:
        self.registry = registry
        self.perf_model = perf_model

    def select(self, op: str, batch_size: int, seq_len: int, hidden_dim: int, backend: Optional[str] = None) -> KernelSpec:
        candidates = self.registry.query(op, backend=backend)
        if not candidates:
            raise ValueError(f"No kernel registered for op={op}")
        best = min(candidates, key=lambda k: self.perf_model.predict(k, batch_size, seq_len, hidden_dim))
        return best
