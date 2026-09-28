from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class MemorySnapshot:
    timestamp: float
    allocated_gb: float
    reserved_gb: float
    peak_allocated_gb: float
    cpu_mem_gb: float
    layer_id: str | None = None


@dataclass
class ComputeSnapshot:
    timestamp: float
    layer_id: str
    flops: int
    macs: int
    duration_ms: float


@dataclass
class TokenProbabilityEntry:
    step: int
    token_id: int
    log_prob: float
    top_k: list[tuple[int, float]]


class MemoryProfiler:
    def __init__(self) -> None:
        self._snapshots: list[MemorySnapshot] = []

    def start(self) -> None:
        self._snapshots = torch.cuda.reset_peak_memory_stats()
        self._snapshots = []

    def take_snapshot(self, layer_id: str | None = None) -> MemorySnapshot:
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            peak = torch.cuda.max_memory_allocated() / (1024**3)
        else:
            allocated = reserved = peak = 0.0
        cpu_mem = 0.0
        try:
            import psutil

            cpu_mem = psutil.Process().memory_info().rss / (1024**3)
        except Exception:
            pass
        snap = MemorySnapshot(
            timestamp=time.time(),
            allocated_gb=round(allocated, 6),
            reserved_gb=round(reserved, 6),
            peak_allocated_gb=round(peak, 6),
            cpu_mem_gb=round(cpu_mem, 6),
            layer_id=layer_id,
        )
        self._snapshots.append(snap)
        return snap

    def summary(self) -> dict[str, Any]:
        if not self._snapshots:
            return {}
        allocated = [s.allocated_gb for s in self._snapshots]
        reserved = [s.reserved_gb for s in self._snapshots]
        cpu = [s.cpu_mem_gb for s in self._snapshots]
        return {
            "snapshots": len(self._snapshots),
            "max_allocated_gb": round(max(allocated), 6),
            "max_reserved_gb": round(max(reserved), 6),
            "max_cpu_mem_gb": round(max(cpu), 6),
            "allocated_series": allocated,
            "reserved_series": reserved,
            "cpu_series": cpu,
        }


class ComputeProfiler:
    def __init__(self) -> None:
        self._snapshots: list[ComputeSnapshot] = []

    def profile_layer(self, module: nn.Module, layer_id: str, input_tensor: torch.Tensor) -> ComputeSnapshot:
        start = time.perf_counter()
        flops = int(torch.numel(input_tensor))
        macs = flops // 2
        with torch.no_grad():
            module(input_tensor)
        duration_ms = (time.perf_counter() - start) * 1000.0
        snap = ComputeSnapshot(
            timestamp=time.time(),
            layer_id=layer_id,
            flops=flops,
            macs=macs,
            duration_ms=round(duration_ms, 4),
        )
        self._snapshots.append(snap)
        return snap

    def summary(self) -> dict[str, Any]:
        if not self._snapshots:
            return {}
        durations = [s.duration_ms for s in self._snapshots]
        flops_list = [s.flops for s in self._snapshots]
        return {
            "layers": len(self._snapshots),
            "total_duration_ms": round(sum(durations), 4),
            "avg_duration_ms": round(sum(durations) / len(durations), 4),
            "max_duration_ms": round(max(durations), 4),
            "total_flops": sum(flops_list),
            "entries": [
                {
                    "layer_id": s.layer_id,
                    "flops": s.flops,
                    "macs": s.macs,
                    "duration_ms": s.duration_ms,
                }
                for s in self._snapshots
            ],
        }


class TokenProbabilityTracker:
    def __init__(self, top_k: int = 10) -> None:
        self._entries: list[TokenProbabilityEntry] = []
        self._top_k = top_k

    def log_step(self, step: int, logits: torch.Tensor, token_id: int) -> None:
        log_probs = torch.log_softmax(logits, dim=-1)
        log_prob = float(log_probs[..., token_id].item())
        top_values, top_indices = torch.topk(log_probs, k=min(self._top_k, log_probs.size(-1)), dim=-1)
        top_k = [
            (int(top_indices[..., i].item()), float(top_values[..., i].item()))
            for i in range(top_indices.size(-1))
        ]
        self._entries.append(TokenProbabilityEntry(step=step, token_id=token_id, log_prob=log_prob, top_k=top_k))

    def history(self) -> list[dict[str, Any]]:
        return [
            {
                "step": e.step,
                "token_id": e.token_id,
                "log_prob": e.log_prob,
                "top_k": e.top_k,
            }
            for e in self._entries
        ]

    def summary(self) -> dict[str, Any]:
        if not self._entries:
            return {}
        return {
            "steps": len(self._entries),
            "history": self.history(),
        }
