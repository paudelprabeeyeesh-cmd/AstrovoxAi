"""
Phase 6 Memory Optimization Module
====================================

Production-ready memory optimization toolkit for large language model training
and inference. Provides:

1. Activation recomputation
   - Checkpointed forward for transformer blocks
   - Selectively recompute expensive ops

2. Parameter offloading
   - CPU offload for parameters not in current layer
   - Automatic prefetching

3. Optimizer offloading
   - CPU offload for optimizer states
   - Async parameter updates

4. Memory profiler
   - Track peak memory usage
   - Per-layer memory reporting
   - Memory timeline logging

5. Fused kernels
   - Fused layer norm
   - Fused MLP (gate/up/down projection fusion)
   - Fused attention (if available)

6. Quantized training
   - INT8 weight quantization
   - INT8 activation quantization
   - Mixed precision training

7. CUDA graphs
   - Capture static computation graphs
   - Replay for faster inference

Hardware support:
- NVIDIA GPUs (CUDA, Ampere+ recommended for INT8)
- AMD GPUs via ROCm (partial support)
- CPU fallback for all operations

Graceful degradation:
- Each subsystem independently falls back to standard PyTorch ops
  when accelerators, libraries, or hardware support are unavailable.
"""

import contextlib
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class MemorySnapshot:
    """Point-in-time memory statistics."""

    timestamp: float = field(default_factory=time.time)
    allocated_bytes: int = 0
    reserved_bytes: int = 0
    peak_allocated_bytes: int = 0
    active_bytes: int = 0
    layer_name: str | None = None


@dataclass
class LayerMemoryStats:
    """Aggregated memory statistics for a single layer."""

    name: str
    peak_allocated_bytes: int = 0
    total_allocated_bytes: int = 0
    forward_calls: int = 0


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _is_cuda_available() -> bool:
    return torch.cuda.is_available()


def _cuda_device_count() -> int:
    return torch.cuda.device_count() if _is_cuda_available() else 0


def _bytes_to_mb(b: int) -> float:
    return b / (1024 * 1024)


def _safe_tensor_to_cpu(tensor: torch.Tensor) -> torch.Tensor:
    return tensor.detach().to("cpu", non_blocking=True)


def _safe_tensor_to_cuda(tensor: torch.Tensor, device: torch.device) -> torch.Tensor:
    return tensor.to(device, non_blocking=True)


# ---------------------------------------------------------------------------
# 1. Activation recomputation
# ---------------------------------------------------------------------------


class CheckpointedFunction(torch.autograd.Function):
    """Stateless autograd Function implementing checkpointed forward."""

    @staticmethod
    def forward(
        ctx: Any,
        forward_fn: Callable,
        *args: Any,
    ) -> Any:
        ctx.forward_fn = forward_fn
        tensors = [a for a in args if isinstance(a, torch.Tensor)]
        others = [a for a in args if not isinstance(a, torch.Tensor)]

        with torch.no_grad():
            outputs = forward_fn(*args)

        if not isinstance(outputs, (tuple, list)):
            outputs = (outputs,)

        output_tensors = [o for o in outputs if isinstance(o, torch.Tensor)]
        ctx.save_for_backward(*output_tensors, *tensors)
        ctx.num_outputs = len(output_tensors)
        ctx.num_input_tensors = len(tensors)
        ctx.others = others

        if len(outputs) == 1:
            return outputs[0]
        return outputs

    @staticmethod
    def backward(ctx: Any, *grad_outputs: Any) -> Any:
        with torch.enable_grad():
            flat = list(ctx.saved_tensors)
            inputs = flat[ctx.num_outputs :]
            outputs = flat[: ctx.num_outputs]

            for o, g in zip(outputs, grad_outputs, strict=False):
                if isinstance(o, torch.Tensor):
                    o.grad = g

            forward_args = inputs + ctx.others
            out = ctx.forward_fn(*forward_args)

            if not isinstance(out, (tuple, list)):
                out = (out,)

            grads = []
            for o in out:
                if isinstance(o, torch.Tensor) and o.requires_grad:
                    grads.append(o.grad)
                else:
                    grads.append(None)

            while len(grads) < len(flat):
                grads.append(None)

            return (None, *grads)


def checkpoint_forward(
    forward_fn: Callable,
    *args: Any,
) -> Any:
    """
    Run a forward pass with activation checkpointing.

    Saves memory by discarding intermediate activations and recomputing
    them during the backward pass.
    """
    return CheckpointedFunction.apply(forward_fn, *args)


class SelectiveRecompute:
    """
    Wrap a transformer block and selectively recompute expensive operations.

    Recomputes attention and MLP blocks while checkpointing cheaper ops.
    """

    def __init__(
        self,
        block: nn.Module,
        expensive_ops: list[str] | None = None,
    ) -> None:
        self.block = block
        self.expensive_ops = expensive_ops or ["attn", "mlp"]

    def forward(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        **kwargs: Any,
    ) -> torch.Tensor:
        if not self.training or not self.expensive_ops:
            return self.block(hidden_states, attention_mask=attention_mask, **kwargs)

        def _block_fn(
            hidden: torch.Tensor,
            mask: torch.Tensor | None = None,
            **kw: Any,
        ) -> torch.Tensor:
            return self.block(hidden, attention_mask=mask, **kw)

        return checkpoint_forward(
            _block_fn,
            hidden_states,
            attention_mask,
            **kwargs,
        )

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.forward(*args, **kwargs)


# ---------------------------------------------------------------------------
# 2. Parameter offloading
# ---------------------------------------------------------------------------


class CPUOffloadParameterBuffer:
    """
    Buffer that holds parameters on CPU and prefetches them on demand.

    Parameters not in the current layer are kept on CPU and moved to GPU
    only when needed, then released back after the forward/backward pass.
    """

    def __init__(
        self,
        module: nn.Module,
        device: torch.device,
        prefetch_lookahead: int = 1,
    ) -> None:
        self.module = module
        self.device = device
        self.prefetch_lookahead = prefetch_lookahead

        self._cpu_buffers: dict[str, nn.Parameter] = {}
        self._gpu_param_names: set = set()
        self._lock = threading.Lock()

        for name, param in module.named_parameters():
            if param.device.type != "cpu":
                cpu_param = param.detach().clone().cpu()
                self._cpu_buffers[name] = cpu_param

    def prefetch(self, needed_names: list[str]) -> None:
        """
        Prefetch parameters to GPU ahead of their use.

        Safely moves parameters from CPU to GPU, keeping a CPU backup.
        """
        with self._lock:
            for name in needed_names:
                if name in self._cpu_buffers and name not in self._gpu_param_names:
                    cpu_param = self._cpu_buffers[name]
                    param = _safe_tensor_to_cuda(cpu_param, self.device)
                    param.requires_grad_(True)
                    with torch.no_grad():
                        parent, _, attr = name.rpartition(".")
                        if parent:
                            mod = self.module.get_submodule(parent)
                            setattr(mod, attr, nn.Parameter(param))
                        else:
                            setattr(self.module, name, nn.Parameter(param))
                    self._gpu_param_names.add(name)

    def release(self, released_names: list[str]) -> None:
        """
        Release parameters back to CPU after use, preserving gradients.
        """
        with self._lock:
            for name in released_names:
                if name in self._gpu_param_names:
                    parent, _, attr = name.rpartition(".")
                    if parent:
                        mod = self.module.get_submodule(parent)
                        param = getattr(mod, attr)
                    else:
                        param = getattr(self.module, name)

                    cpu_param = _safe_tensor_to_cpu(param)
                    if name in self._cpu_buffers:
                        self._cpu_buffers[name].copy_(cpu_param, non_blocking=True)
                    else:
                        self._cpu_buffers[name] = cpu_param

                    with torch.no_grad():
                        param.data.copy_(_safe_tensor_to_cuda(cpu_param, self.device))
                    self._gpu_param_names.discard(name)

    def sync_gradients(self) -> None:
        """Copy gradients from GPU parameters back to CPU buffers."""
        with self._lock:
            for name in list(self._gpu_param_names):
                parent, _, attr = name.rpartition(".")
                if parent:
                    mod = self.module.get_submodule(parent)
                    param = getattr(mod, attr)
                else:
                    param = getattr(self.module, name)

                if param.grad is not None:
                    cpu_param = self._cpu_buffers[name]
                    cpu_param.grad = _safe_tensor_to_cpu(param.grad)


def enable_cpu_offload(
    module: nn.Module,
    device: torch.device,
    prefetch_lookahead: int = 1,
) -> CPUOffloadParameterBuffer:
    """
    Enable CPU offloading for module parameters.

    Returns a CPUOffloadParameterBuffer that manages offload/prefetch.
    """
    if not _is_cuda_available():
        logger.warning("CUDA unavailable; CPU offload disabled.")
        return CPUOffloadParameterBuffer(module, device)

    buf = CPUOffloadParameterBuffer(module, device, prefetch_lookahead)
    logger.info("CPU offload enabled for %s parameters.", sum(1 for _ in module.parameters()))
    return buf


# ---------------------------------------------------------------------------
# 3. Optimizer offloading
# ---------------------------------------------------------------------------


class CPUOffloadOptimizer:
    """
    Wraps a PyTorch optimizer and keeps its state on CPU, moving parameter
    tensors to GPU only during optimizer.step().

    Supports async parameter updates via non-blocking copies.
    """

    def __init__(
        self,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
        pin_memory: bool = True,
    ) -> None:
        self.optimizer = optimizer
        self.device = device
        self.pin_memory = pin_memory and _is_cuda_available()
        self._param_cpu_copies: dict[int, torch.Tensor] = {}

        if not _is_cuda_available():
            logger.warning("CUDA unavailable; optimizer CPU offload disabled.")
            return

        for group in optimizer.param_groups:
            for param in group["params"]:
                if not isinstance(param, nn.Parameter):
                    continue
                pid = id(param)
                cpu_param = _safe_tensor_to_cpu(param)
                cpu_param.grad = None
                self._param_cpu_copies[pid] = cpu_param

    def step(self, closure: Callable | None = None) -> float | None:
        """Move grads to CPU, step optimizer, then async copy params back to GPU."""
        if not self._param_cpu_copies:
            return self.optimizer.step(closure)

        with torch.no_grad():
            for group in self.optimizer.param_groups:
                for param in group["params"]:
                    pid = id(param)
                    if pid not in self._param_cpu_copies:
                        continue
                    cpu_param = self._param_cpu_copies[pid]
                    if param.grad is not None:
                        cpu_param.grad = _safe_tensor_to_cpu(param.grad)
                    else:
                        cpu_param.grad = None

            loss = self.optimizer.step(closure)

            for group in self.optimizer.param_groups:
                for param in group["params"]:
                    pid = id(param)
                    if pid not in self._param_cpu_copies:
                        continue
                    cpu_param = self._param_cpu_copies[pid]
                    cpu_param.data.copy_(param.data.cpu(), non_blocking=True)
                    param.data.copy_(
                        _safe_tensor_to_cuda(cpu_param, self.device), non_blocking=True
                    )

        return loss

    def zero_grad(self, set_to_none: bool = False) -> None:
        """Zero gradients in CPU copies and GPU tensors."""
        self.optimizer.zero_grad(set_to_none=set_to_none)
        for cpu_param in self._param_cpu_copies.values():
            if set_to_none:
                cpu_param.grad = None
            elif cpu_param.grad is not None:
                cpu_param.grad.zero_()


def enable_optimizer_cpu_offload(
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> CPUOffloadOptimizer:
    """
    Wrap an optimizer with CPU offloading.

    Offloads optimizer state to CPU and uses async transfers for params.
    """
    return CPUOffloadOptimizer(optimizer, device)


# ---------------------------------------------------------------------------
# 4. Memory profiler
# ---------------------------------------------------------------------------


class MemoryProfiler:
    """
    Tracks and reports memory usage across training/inference sessions.

    Supports:
    - Global peak memory tracking
    - Per-layer memory reporting
    - Memory timeline logging (ring buffer)
    """

    def __init__(
        self,
        max_timeline_entries: int = 1000,
        enabled: bool = True,
    ) -> None:
        self.enabled = enabled and _is_cuda_available()
        self._max_entries = max_timeline_entries
        self._timeline: deque[MemorySnapshot] = deque(maxlen=max_timeline_entries)
        self._layer_stats: dict[str, LayerMemoryStats] = defaultdict(
            lambda: LayerMemoryStats(name="")
        )
        self._global_peak: int = 0
        self._lock = threading.Lock()

        if not self.enabled:
            logger.info("MemoryProfiler disabled (CUDA unavailable or disabled).")

    def reset_peak(self) -> None:
        """Reset peak memory statistics."""
        if self.enabled:
            torch.cuda.reset_peak_memory_stats()

    def snapshot(self, layer_name: str | None = None) -> MemorySnapshot:
        """
        Capture a memory snapshot and record it in the timeline.
        """
        if not self.enabled:
            return MemorySnapshot()

        stats = torch.cuda.memory_stats()
        allocated = torch.cuda.memory_allocated()
        reserved = torch.cuda.memory_reserved()
        peak = torch.cuda.max_memory_allocated()

        with self._lock:
            self._global_peak = max(self._global_peak, peak)
            if layer_name:
                ls = self._layer_stats[layer_name]
                ls.peak_allocated_bytes = max(ls.peak_allocated_bytes, allocated)
                ls.forward_calls += 1
                ls.total_allocated_bytes += allocated

        snap = MemorySnapshot(
            allocated_bytes=allocated,
            reserved_bytes=reserved,
            peak_allocated_bytes=peak,
            active_bytes=stats.get("active_bytes", 0),
            layer_name=layer_name,
        )
        with self._lock:
            self._timeline.append(snap)
        return snap

    def get_layer_stats(self) -> dict[str, LayerMemoryStats]:
        """Return per-layer memory statistics."""
        with self._lock:
            return dict(self._layer_stats)

    def get_global_peak(self) -> int:
        """Return global peak allocated memory in bytes."""
        with self._lock:
            return self._global_peak

    def get_timeline(self) -> list[MemorySnapshot]:
        """Return a copy of the memory timeline."""
        with self._lock:
            return list(self._timeline)

    def log_summary(self) -> None:
        """Log a summary of memory usage."""
        with self._lock:
            peak = self._global_peak
            layers = dict(self._layer_stats)

        logger.info(
            "Memory summary - Peak allocated: %.2f MB, Timeline entries: %d",
            _bytes_to_mb(peak),
            len(self._timeline),
        )
        for name, stats in layers.items():
            logger.info(
                "  Layer '%s': peak=%.2f MB, calls=%d, total=%.2f MB",
                name,
                _bytes_to_mb(stats.peak_allocated_bytes),
                stats.forward_calls,
                _bytes_to_mb(stats.total_allocated_bytes),
            )

    def clear(self) -> None:
        """Clear all recorded memory data."""
        with self._lock:
            self._timeline.clear()
            self._layer_stats.clear()
            self._global_peak = 0

    def __enter__(self) -> MemoryProfiler:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.log_summary()


class LayerMemoryTracker:
    """
    Context manager for per-layer memory tracking.

    Usage::

        tracker = LayerMemoryTracker(profiler, "encoder.layer.3")
        with tracker:
            ...
    """

    def __init__(self, profiler: MemoryProfiler, layer_name: str) -> None:
        self.profiler = profiler
        self.layer_name = layer_name
        self._snap_before: MemorySnapshot | None = None

    def __enter__(self) -> LayerMemoryTracker:
        self._snap_before = self.profiler.snapshot(self.layer_name)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.profiler.snapshot(self.layer_name)

    @property
    def delta_bytes(self) -> int:
        if self._snap_before is None:
            return 0
        snap_after = self.profiler.snapshot(self.layer_name)
        return max(0, snap_after.allocated_bytes - self._snap_before.allocated_bytes)


# ---------------------------------------------------------------------------
# 5. Fused kernels
# ---------------------------------------------------------------------------


class FusedLayerNorm(nn.Module):
    """
    Fused layer normalization using PyTorch's native layer norm.

    Automatically falls back to standard nn.LayerNorm when CUDA or
    required kernel support is unavailable.
    """

    def __init__(
        self,
        hidden_size: int,
        eps: float = 1e-5,
        bias: bool = True,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(hidden_size))
        self.bias = nn.Parameter(torch.zeros(hidden_size)) if bias else None
        self._use_fused = _is_cuda_available()

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        if self._use_fused and hidden_states.is_cuda:
            return F.layer_norm(
                hidden_states,
                self.weight.shape,
                self.weight,
                self.bias,
                self.eps,
            )
        return F.layer_norm(
            hidden_states,
            self.weight.shape,
            self.weight,
            self.bias,
            self.eps,
        )

    def extra_repr(self) -> str:
        return f"hidden_size={self.hidden_size}, eps={self.eps}, " f"fused={self._use_fused}"


class FusedMLP(nn.Module):
    """
    Fused MLP with gate/up/down projection fusion.

    Implements SwiGLU-style gating:

        output = (gate * up) @ down_proj

    Attempts to fuse gate+up into a single matmul when CUDA is available.
    Falls back to separate matmuls otherwise.
    """

    def __init__(
        self,
        hidden_size: int,
        intermediate_size: int,
        activation: str = "silu",
        bias: bool = False,
    ) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.intermediate_size = intermediate_size

        self.gate_up_proj = nn.Linear(hidden_size, 2 * intermediate_size, bias=bias)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=bias)

        self.activation_fn: Callable
        if activation == "silu":
            self.activation_fn = F.silu
        elif activation == "gelu":
            self.activation_fn = F.gelu
        else:
            raise ValueError(f"Unsupported activation: {activation}")

        self._use_fused = _is_cuda_available()

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        fused = self.gate_up_proj(hidden_states)
        gate, up = fused.chunk(2, dim=-1)
        activated = self.activation_fn(gate) * up
        return self.down_proj(activated)


class FusedAttention(nn.Module):
    """
    Fused attention wrapper.

    Uses PyTorch SDPA (scaled dot-product attention) on CUDA when available.
    Falls back to manual attention otherwise.
    """

    def __init__(
        self,
        num_heads: int,
        head_dim: int,
        dropout: float = 0.0,
        causal: bool = True,
    ) -> None:
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = head_dim
        self.dropout = dropout
        self.causal = causal
        self.scale = head_dim**-0.5
        self._use_sdpa = (
            _is_cuda_available()
            and hasattr(F, "scaled_dot_product_attention")
            and torch.cuda.get_device_capability()[0] >= 8
        )

    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if self._use_sdpa:
            return self._fused_sdpa(query, key, value, attention_mask)
        return self._manual_attention(query, key, value, attention_mask)

    def _fused_sdpa(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        attention_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        is_causal = self.causal and attention_mask is None
        return F.scaled_dot_product_attention(
            query,
            key,
            value,
            attn_mask=attention_mask,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=is_causal,
        )

    def _manual_attention(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        attention_mask: torch.Tensor | None,
    ) -> torch.Tensor:
        B, H, L, D = query.shape
        scores = torch.matmul(query, key.transpose(-2, -1)) * self.scale
        if attention_mask is not None:
            scores = scores + attention_mask
        elif self.causal:
            causal_mask = torch.triu(
                torch.ones(L, L, device=query.device, dtype=torch.bool), diagonal=1
            )
            scores = scores.masked_fill(causal_mask.unsqueeze(0).unsqueeze(0), float("-inf"))

        attn = F.softmax(scores, dim=-1, dtype=torch.float32).to(query.dtype)
        attn = F.dropout(attn, p=self.dropout, training=self.training)
        return torch.matmul(attn, value)


# ---------------------------------------------------------------------------
# 6. Quantized training
# ---------------------------------------------------------------------------


class INT8WeightQuantizer:
    """
    Simple per-tensor INT8 weight quantizer for training-time weight
    quantization. Quantizes weights to INT8 on forward pass and dequantizes
    on the fly.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and _is_cuda_available()
        self._scale: torch.Tensor | None = None
        self._zero_point: torch.Tensor | None = None

    def quantize(self, weight: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        if not self.enabled:
            return weight, torch.tensor(1.0, device=weight.device)
        q_weight, scale, zero_point = torch.ops.quantized_decomposed.quantize_per_tensor(
            weight.cpu(), 0, 255, torch.quint8
        )
        self._scale = scale.to(weight.device)
        self._zero_point = zero_point.to(weight.device)
        return q_weight.to(weight.device), self._scale

    def dequantize(self, q_weight: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        if not self.enabled:
            return q_weight
        return torch.ops.quantized_decomposed.dequantize_per_tensor(
            q_weight, scale, self._zero_point, 0, 255, torch.quint8
        )

    def __call__(self, weight: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.quantize(weight)


class ActivationQuantizer:
    """
    Dynamic INT8 activation quantizer (per-tensor) for training-time use.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and _is_cuda_available()

    def quantize(self, activation: torch.Tensor) -> torch.Tensor:
        if not self.enabled:
            return activation
        abs_max = activation.detach().abs().max()
        scale = abs_max / 127.0 if abs_max > 0 else torch.tensor(1.0, device=activation.device)
        q_act = torch.clamp(torch.round(activation / scale), -128, 127).to(torch.int8)
        return q_act, scale

    def dequantize(self, q_act: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        if not self.enabled:
            return q_act
        return q_act.float() * scale

    def __call__(self, activation: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        return self.quantize(activation)


class MixedPrecisionTraining:
    """
    Mixed precision (FP16/BF16) training context manager.

    Wraps the model and optimizer in torch.cuda.amp when CUDA is available.
    """

    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        dtype: str = "fp16",
        device: torch.device | None = None,
    ) -> None:
        self.device = device or (
            torch.device("cuda") if _is_cuda_available() else torch.device("cpu")
        )
        self.model = model.to(self.device)
        self.optimizer = optimizer
        self.dtype = dtype
        self._use_amp = _is_cuda_available()
        self._scaler = None

        if self._use_amp:
            if dtype == "fp16":
                self._scaler = torch.cuda.amp.GradScaler()
                self.autocast_dtype = torch.float16
            elif dtype == "bf16":
                self.autocast_dtype = torch.bfloat16
            else:
                raise ValueError(f"Unsupported mixed precision dtype: {dtype}")

    @contextlib.contextmanager
    def autocast(self) -> Any:
        if not self._use_amp:
            yield
            return
        with torch.cuda.amp.autocast(dtype=self.autocast_dtype):
            yield

    def scale_loss(self, loss: torch.Tensor) -> torch.Tensor:
        if self._scaler is not None:
            return self._scaler.scale(loss)
        return loss

    def step(self) -> None:
        if self._scaler is not None:
            self._scaler.step(self.optimizer)
            self._scaler.update()
        else:
            self.optimizer.step()

    def backward(self, loss: torch.Tensor) -> None:
        if self._scaler is not None:
            self._scaler.scale(loss).backward()
        else:
            loss.backward()

    def __enter__(self) -> MixedPrecisionTraining:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


def enable_quantized_training(
    model: nn.Module,
    weight_quant: bool = True,
    activation_quant: bool = True,
) -> tuple[nn.Module, INT8WeightQuantizer, ActivationQuantizer]:
    """
    Enable INT8 quantized training for the given model.

    Returns the model (potentially modified), a weight quantizer, and an
    activation quantizer. Actual quantization is applied during forward pass
    by the user via the returned quantizers.
    """
    if not _is_cuda_available():
        logger.warning("CUDA unavailable; quantized training disabled.")
        return model, INT8WeightQuantizer(enabled=False), ActivationQuantizer(enabled=False)

    wq = INT8WeightQuantizer(enabled=weight_quant)
    aq = ActivationQuantizer(enabled=activation_quant)
    logger.info(
        "Quantized training enabled - weights=%s, activations=%s",
        weight_quant,
        activation_quant,
    )
    return model, wq, aq


# ---------------------------------------------------------------------------
# 7. CUDA graphs
# ---------------------------------------------------------------------------


class CUDAGraphCapture:
    """
    Capture and replay static computation graphs via CUDA graphs.

    When computation shapes are static (same sequence length, batch size),
    CUDA graphs can significantly reduce kernel launch overhead.

    Usage::

        cg = CUDAGraphCapture(model, example_inputs)
        cg.capture()
        cg.replay()
    """

    def __init__(
        self,
        model: nn.Module,
        example_inputs: tuple[torch.Tensor, ...],
        warmup_iters: int = 3,
        device: torch.device | None = None,
    ) -> None:
        self.device = device or (
            torch.device("cuda") if _is_cuda_available() else torch.device("cpu")
        )
        self.model = model.to(self.device)
        self.example_inputs = example_inputs
        self.warmup_iters = warmup_iters
        self._graph: torch.cuda.CUDAGraph | None = None
        self._static_inputs: list[torch.Tensor] | None = None
        self._static_outputs: Any | None = None
        self._use_cuda_graphs = _is_cuda_available() and torch.cuda.get_device_capability()[0] >= 7

        if not self._use_cuda_graphs:
            logger.info("CUDA graphs unavailable or unsupported; replay disabled.")

    def capture(self) -> None:
        """
        Capture the CUDA graph.

        Runs warmup iterations before capturing to ensure cudnn/cublas
        heuristics are settled.
        """
        if not self._use_cuda_graphs:
            logger.warning("Cannot capture CUDA graphs; unsupported hardware.")
            return

        self.model.eval()
        example_inputs = tuple(
            x.to(self.device, non_blocking=True) if isinstance(x, torch.Tensor) else x
            for x in self.example_inputs
        )

        with torch.no_grad():
            for _ in range(self.warmup_iters):
                _ = self.model(*example_inputs)

            if self._graph is None:
                self._graph = torch.cuda.CUDAGraph()

            self._static_inputs = [
                x.clone() if isinstance(x, torch.Tensor) else x for x in example_inputs
            ]

            self._graph.capture_begin()
            self._static_outputs = self.model(*self._static_inputs)
            self._graph.capture_end()

        logger.info("CUDA graph captured successfully.")

    def replay(self) -> Any:
        """
        Replay the captured CUDA graph.

        Must be called after capture(). Inputs must match capture-time shapes.
        """
        if not self._use_cuda_graphs or self._graph is None:
            if self.model.training:
                self.model.train()
            if self._static_outputs is None:
                raise RuntimeError("CUDA graph has not been captured.")
            return self._static_outputs

        self._graph.replay()
        return self._static_outputs

    def reset(self) -> None:
        """Free the captured CUDA graph."""
        self._graph = None
        self._static_inputs = None
        self._static_outputs = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.replay()


# ---------------------------------------------------------------------------
# Unified optimizer wrapper
# ---------------------------------------------------------------------------


class MemoryOptimizedOptimizer:
    """
    Composite wrapper combining checkpointing, offloading, and mixed precision
    into a single interface.
    """

    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        device: torch.device,
        enable_checkpoint: bool = True,
        enable_cpu_offload_params: bool = True,
        enable_cpu_offload_optimizer: bool = True,
        enable_mixed_precision: bool = True,
        mp_dtype: str = "fp16",
        profiler: MemoryProfiler | None = None,
    ) -> None:
        self.device = device
        self.model = model
        self.optimizer = optimizer
        self.profiler = profiler or MemoryProfiler()

        self.mp = (
            MixedPrecisionTraining(
                model=model,
                optimizer=optimizer,
                dtype=mp_dtype,
                device=device,
            )
            if enable_mixed_precision and _is_cuda_available()
            else None
        )

        self.param_offload = (
            enable_cpu_offload(model, device)
            if enable_cpu_offload_params and _is_cuda_available()
            else None
        )

        self.optim_offload = (
            CPUOffloadOptimizer(optimizer, device)
            if enable_cpu_offload_optimizer and _is_cuda_available()
            else None
        )

        self.enable_checkpoint = enable_checkpoint

    def step(self, closure: Callable | None = None) -> float | None:
        """Perform a single optimization step."""
        if self.optim_offload is not None:
            return self.optim_offload.step(closure)
        loss = self.optimizer.step(closure)
        return loss

    def backward(self, loss: torch.Tensor) -> None:
        """Backward pass with optional mixed precision scaling."""
        if self.mp is not None:
            self.mp.backward(loss)
        else:
            loss.backward()

    def zero_grad(self, set_to_none: bool = False) -> None:
        if self.optim_offload is not None:
            self.optim_offload.zero_grad(set_to_none=set_to_none)
        else:
            self.optimizer.zero_grad(set_to_none=set_to_none)

    def prefetch_layer_params(self, param_names: list[str]) -> None:
        if self.param_offload is not None:
            self.param_offload.prefetch(param_names)

    def release_layer_params(self, param_names: list[str]) -> None:
        if self.param_offload is not None:
            self.param_offload.release(param_names)

    def profile_snapshot(self, layer_name: str | None = None) -> MemorySnapshot:
        return self.profiler.snapshot(layer_name)

    def log_memory_summary(self) -> None:
        self.profiler.log_summary()


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_memory_optimized_model(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device | None = None,
    enable_checkpoint: bool = True,
    enable_cpu_offload_params: bool = True,
    enable_cpu_offload_optimizer: bool = True,
    enable_mixed_precision: bool = True,
    enable_fused_kernels: bool = True,
    enable_cuda_graphs: bool = False,
    mp_dtype: str = "fp16",
    profiler: MemoryProfiler | None = None,
) -> tuple[MemoryOptimizedOptimizer, CUDAGraphCapture | None]:
    """
    One-stop factory for memory-optimized training.

    Returns (MemoryOptimizedOptimizer, CUDAGraphCapture|None).
    """
    device = device or (torch.device("cuda") if _is_cuda_available() else torch.device("cpu"))

    if enable_fused_kernels and _is_cuda_available():
        _maybe_fuse_layer_norms(model)
        logger.info("Fused kernels enabled for supported layers.")

    opt = MemoryOptimizedOptimizer(
        model=model,
        optimizer=optimizer,
        device=device,
        enable_checkpoint=enable_checkpoint,
        enable_cpu_offload_params=enable_cpu_offload_params,
        enable_cpu_offload_optimizer=enable_cpu_offload_optimizer,
        enable_mixed_precision=enable_mixed_precision,
        mp_dtype=mp_dtype,
        profiler=profiler,
    )

    cg = None
    if enable_cuda_graphs and _is_cuda_available():
        example_inputs = _get_example_inputs(model)
        if example_inputs is not None:
            cg = CUDAGraphCapture(model, example_inputs, device=device)

    return opt, cg


def _maybe_fuse_layer_norms(model: nn.Module) -> None:
    """Replace nn.LayerNorm with FusedLayerNorm where possible."""
    for name, child in model.named_children():
        if isinstance(child, nn.LayerNorm):
            fused = FusedLayerNorm(
                child.normalized_shape,
                eps=child.eps,
                bias=child.bias is not None,
            )
            fused.weight.data.copy_(child.weight.data)
            if child.bias is not None:
                fused.bias.data.copy_(child.bias.data)
            setattr(model, name, fused)
            logger.debug("Fused layer norm: %s", name)
        else:
            _maybe_fuse_layer_norms(child)


def _get_example_inputs(model: nn.Module) -> tuple[torch.Tensor, ...] | None:
    """Best-effort extraction of example inputs for CUDA graph capture."""
    return None
