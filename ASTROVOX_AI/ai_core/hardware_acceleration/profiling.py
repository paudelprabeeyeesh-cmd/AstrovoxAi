from __future__ import annotations

import logging
import json
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class HardwareProfiler:
    def __init__(self, device: int = 0):
        self.device = device
        self.metrics: List[Dict[str, Any]] = []
        self.memory_snapshots: List[Dict[str, int]] = []

    def profile_model(self, model: nn.Module, inputs: Tuple[torch.Tensor, ...]) -> Dict[str, Any]:
        if not torch.cuda.is_available():
            return {"device": "cpu", "throughput": 0.0, "latency_ms": 0.0}
        model = model.to(f"cuda:{self.device}")
        inputs = tuple(t.to(f"cuda:{self.device}") for t in inputs)
        torch.cuda.synchronize()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        model(*inputs)
        end.record()
        torch.cuda.synchronize()
        latency_ms = start.elapsed_time(end)
        result = {
            "device": "cuda",
            "latency_ms": latency_ms,
            "throughput": 1000.0 / latency_ms if latency_ms > 0 else 0.0,
            "memory_allocated_mb": torch.cuda.memory_allocated(self.device) / 1e6,
            "memory_reserved_mb": torch.cuda.memory_reserved(self.device) / 1e6,
        }
        self.metrics.append(result)
        return result

    def get_memory_usage(self) -> Dict[str, int]:
        if not torch.cuda.is_available():
            return {"allocated": 0, "reserved": 0, "max_allocated": 0}
        return {
            "allocated": torch.cuda.memory_allocated(self.device),
            "reserved": torch.cuda.memory_reserved(self.device),
            "max_allocated": torch.cuda.max_memory_allocated(self.device),
        }

    def report(self) -> Dict[str, Any]:
        if not self.metrics:
            return {"status": "no_data"}
        latencies = [m["latency_ms"] for m in self.metrics]
        throughputs = [m["throughput"] for m in self.metrics]
        return {
            "avg_latency_ms": sum(latencies) / len(latencies),
            "avg_throughput": sum(throughputs) / len(throughputs),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "num_runs": len(self.metrics),
        }

    def export_report(self, path: str) -> None:
        report = self.report()
        with open(path, "w") as f:
            json.dump(report, f, indent=2)


class AccelerationBenchmark:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []

    def run_benchmark(self, model: nn.Module, inputs: Tuple[torch.Tensor, ...], backend: str) -> Dict[str, Any]:
        profiler = HardwareProfiler()
        result = profiler.profile_model(model, inputs)
        result["backend"] = backend
        self.results.append(result)
        return result

    def compare_backends(self, model: nn.Module, inputs: Tuple[torch.Tensor, ...], backends: List[str]) -> Dict[str, Dict[str, Any]]:
        return {backend: self.run_benchmark(model, inputs, backend) for backend in backends}

    def get_best_backend(self) -> Optional[str]:
        if not self.results:
            return None
        best = max(self.results, key=lambda r: r.get("throughput", 0))
        return best.get("backend")


class PerformanceAnalyzer:
    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        self.history.append(metrics)
        return {
            "bottleneck": self._detect_bottleneck(metrics),
            "recommendation": self._recommend(metrics),
            "score": self._compute_score(metrics),
        }

    def _detect_bottleneck(self, metrics: Dict[str, Any]) -> str:
        if metrics.get("memory_utilization", 0) > 0.9:
            return "memory"
        if metrics.get("compute_utilization", 0) > 0.9:
            return "compute"
        if metrics.get("latency_ms", 0) > 100:
            return "latency"
        return "balanced"

    def _recommend(self, metrics: Dict[str, Any]) -> str:
        bottleneck = self._detect_bottleneck(metrics)
        if bottleneck == "memory":
            return "Consider gradient checkpointing or activation offloading"
        if bottleneck == "compute":
            return "Consider mixed precision or kernel fusion"
        if bottleneck == "latency":
            return "Consider batching or model pruning"
        return "Consider scaling batch size"

    def _compute_score(self, metrics: Dict[str, Any]) -> float:
        throughput = metrics.get("throughput", 0)
        latency = metrics.get("latency_ms", 1)
        memory = metrics.get("memory_allocated_mb", 1000)
        return (throughput / 1000) / (latency / 1000 + memory / 10000)
