from __future__ import annotations

import logging
import time
from typing import Optional, Dict, List, Tuple, Callable
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class GPUKernelOptimizer:
    def __init__(self, device: int = 0):
        self.device = device
        self.kernel_cache: Dict[str, Callable] = {}
        self.profiles: Dict[str, List[float]] = {}

    def optimize_linear_layer(self, layer: nn.Linear, input_shape: Tuple[int, ...]) -> nn.Linear:
        if not torch.cuda.is_available():
            return layer
        layer = layer.to(f"cuda:{self.device}")
        if hasattr(torch.cuda, "amp") and hasattr(torch.cuda.amp, "autocast"):
            return layer
        return layer

    def select_optimal_algorithm(self, m: int, k: int, n: int) -> str:
        if not torch.cuda.is_available():
            return "matmul"
        flops = m * k * n
        if flops > 1e9:
            return "tiled_matmul"
        if flops > 1e6:
            return "cublas_gemm"
        return "matmul"

    def profile_kernel(self, kernel_fn: Callable, *args, warmup: int = 10, iterations: int = 100) -> Dict[str, float]:
        if not torch.cuda.is_available():
            return {"latency_ms": 0.0, "throughput": 0.0}
        device = torch.device("cuda")
        for _ in range(warmup):
            kernel_fn(*args)
        torch.cuda.synchronize()
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(iterations):
            kernel_fn(*args)
        end.record()
        torch.cuda.synchronize()
        latency_ms = start.elapsed_time(end) / iterations
        return {"latency_ms": latency_ms, "throughput": 1000.0 / latency_ms if latency_ms > 0 else 0.0}

    def benchmark_matmul(self, m: int, k: int, n: int, dtype: torch.dtype = torch.float32) -> Dict[str, float]:
        if not torch.cuda.is_available():
            return {"algorithm": "cpu", "latency_ms": 0.0}
        a = torch.randn(m, k, device=f"cuda:{self.device}", dtype=dtype)
        b = torch.randn(k, n, device=f"cuda:{self.device}", dtype=dtype)
        algorithm = self.select_optimal_algorithm(m, k, n)
        start = time.perf_counter()
        for _ in range(10):
            torch.matmul(a, b)
        torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - start) / 10 * 1000
        return {"algorithm": algorithm, "m": m, "k": k, "n": n, "latency_ms": latency_ms}

    def optimize_memory_access(self, tensor: torch.Tensor) -> torch.Tensor:
        if not torch.cuda.is_available():
            return tensor.contiguous()
        return tensor.contiguous().to(f"cuda:{self.device}")


class FusedKernelSuite:
    @staticmethod
    def fused_linear_gelu(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        out = torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), x, weight.t())
        return F.gelu(out)

    @staticmethod
    def fused_linear_relu(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        out = torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), x, weight.t())
        return torch.relu(out)

    @staticmethod
    def fused_linear_silu(x: torch.Tensor, weight: torch.Tensor, bias: Optional[torch.Tensor] = None) -> torch.Tensor:
        out = torch.addmm(bias if bias is not None else torch.zeros(weight.size(0), device=x.device, dtype=x.dtype), x, weight.t())
        return F.silu(out)

    @staticmethod
    def fused_rms_norm_linear(x: torch.Tensor, weight: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
        variance = x.pow(2).mean(-1, keepdim=True)
        x = x * torch.rsqrt(variance + eps)
        return weight * x

    @staticmethod
    def fused_dropout_residual_add(x: torch.Tensor, residual: torch.Tensor, dropout: float = 0.1, training: bool = True) -> torch.Tensor:
        return F.dropout(x, p=dropout, training=training) + residual

    @staticmethod
    def fused_attn_qkv_proj(x: torch.Tensor, q_proj: nn.Linear, k_proj: nn.Linear, v_proj: nn.Linear) -> tuple:
        return q_proj(x), k_proj(x), v_proj(x)

    @staticmethod
    def fused_bias_gelu(x: torch.Tensor, bias: torch.Tensor) -> torch.Tensor:
        return F.gelu(x + bias)


class KernelProfiler:
    def __init__(self, device: int = 0):
        self.device = device
        self.profiles: Dict[str, List[float]] = {}

    def profile(self, name: str, fn: Callable, *args, iterations: int = 100) -> Dict[str, float]:
        if not torch.cuda.is_available():
            return {"name": name, "latency_ms": 0.0}
        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        for _ in range(iterations):
            fn(*args)
        end.record()
        torch.cuda.synchronize()
        latency_ms = start.elapsed_time(end) / iterations
        self.profiles.setdefault(name, []).append(latency_ms)
        return {"name": name, "latency_ms": latency_ms}

    def report(self) -> Dict[str, float]:
        return {name: sum(vals) / len(vals) for name, vals in self.profiles.items()}

    def compare(self, name_a: str, name_b: str) -> Dict[str, float]:
        avg_a = sum(self.profiles.get(name_a, [0])) / max(len(self.profiles.get(name_a, [1])), 1)
        avg_b = sum(self.profiles.get(name_b, [0])) / max(len(self.profiles.get(name_b, [1])), 1)
        return {"speedup": avg_b / avg_a if avg_a > 0 else 0.0}
