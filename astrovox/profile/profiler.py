"""Profiler and FLOP accounting.

Measure before optimizing. This module answers the questions that decide
whether a change is worth making: how much arithmetic a step costs, where the
time goes, how much memory is live, and how many buffers were allocated.

FLOP counts follow the convention used by matmul benchmarks, where a
multiply-add is two flops, so a dense matmul of an ``(m, k)`` by a ``(k, n)``
matrix costs ``2 * m * k * n``.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np

from astrovox.autograd.function import GraphNode
from astrovox.autograd.graph import walk_from
from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


def _elements(shape: Shape) -> int:
    """Return the element count of a shape."""
    return shape.numel


def _matmul_flops(a: Shape, b: Shape) -> int:
    """Flops for a batched matmul of ``a`` by ``b``."""
    if a.ndim == 0 or b.ndim == 0:
        return 0
    k = a.dims[-1]
    m = a.dims[-2] if a.ndim >= 2 else 1
    n = b.dims[-1] if b.ndim >= 2 else 1
    batch = _elements(a) // (m * k) if m * k else 1
    return 2 * m * k * n * batch


def _elementwise_flops(shape: Shape) -> int:
    """Flops for one elementwise pass over a shape."""
    return _elements(shape)


def node_flops(node: GraphNode) -> int:
    """Return the flops executed by one graph node's forward pass."""
    name = node.name
    outputs = [o.shape for o in node.outputs if isinstance(o, Tensor)]
    inputs = [i.shape for i in node.inputs if isinstance(i, Tensor)]
    out = outputs[0] if outputs else Shape(())

    if name == "matmul" and len(inputs) >= 2:
        return _matmul_flops(inputs[0], inputs[1])
    if name in {"add", "sub", "mul", "div", "neg", "pow", "relu", "gelu", "silu", "tanh", "sigmoid", "mish"}:
        return _elementwise_flops(out)
    if name in {"exp", "log", "sqrt", "softplus"}:
        return _elementwise_flops(out)
    if name in {"sum", "mean"}:
        return _elementwise_flops(out)
    if name in {"max", "min"}:
        return _elements(out)
    if name in {"layernorm", "rms_norm", "group_norm"}:
        # A mean, a variance, a normalize, a scale and a shift per element.
        return 5 * _elementwise_flops(out)
    if name in {"softmax", "log_softmax"}:
        return 3 * _elementwise_flops(out)
    if name == "cross_entropy":
        # A log-softmax plus a gather over the batch.
        return 3 * _elements(out)
    if name in {"mse_loss", "l1_loss", "bce_loss", "huber_loss"}:
        return _elementwise_flops(out)
    if name in {"view", "reshape", "permute", "transpose", "squeeze", "unsqueeze", "materialize", "slice"}:
        # A view moves no data; materializing copies once per element.
        return _elementwise_flops(out) if name == "materialize" else 0
    if name == "embedding":
        return 0
    if name in {"masked_softmax", "repeat_kv"}:
        return _elementwise_flops(out)
    return 0


@dataclass
class FlopBreakdown:
    """Total flops for a graph, split by operation."""

    total: int = 0
    by_op: dict[str, int] = field(default_factory=dict)
    node_count: int = 0

    def top(self, count: int = 5) -> list[tuple[str, int]]:
        """Return the ``count`` most expensive operations."""
        return sorted(self.by_op.items(), key=lambda kv: -kv[1])[:count]

    def to_dict(self) -> dict[str, Any]:
        """Return the breakdown as a plain dictionary."""
        return {"total": self.total, "node_count": self.node_count, "by_op": self.by_op}


def count_flops(outputs: Tensor | Sequence[Tensor]) -> FlopBreakdown:
    """Count the flops of the forward pass reaching ``outputs``.

    This is a static count over the recorded graph, so it excludes the
    backward pass, which is counted separately by :func:`count_backward_flops`.
    """
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    breakdown = FlopBreakdown()
    for node in walk_from(roots):
        flops = node_flops(node)
        breakdown.total += flops
        breakdown.node_count += 1
        if flops:
            breakdown.by_op[node.name] = breakdown.by_op.get(node.name, 0) + flops
    return breakdown


def count_backward_flops(outputs: Tensor | Sequence[Tensor]) -> FlopBreakdown:
    """Count the flops of the backward pass for the same graph.

    A backward costs roughly twice its forward for most differentiable ops.
    Views and reshapes, which move no data, cost nothing either way.
    """
    forward = count_flops(outputs)
    backward = FlopBreakdown(node_count=forward.node_count)
    for op, flops in forward.by_op.items():
        if op in {"view", "reshape", "permute", "transpose", "squeeze", "unsqueeze", "embedding"}:
            # No elementwise arithmetic to differentiate.
            backward.by_op[op] = 0
            continue
        cost = flops * 2
        backward.by_op[op] = cost
        backward.total += cost
    return backward


@dataclass
class KernelRecord:
    """One timed region of execution."""

    name: str
    seconds: float
    calls: int = 1
    flops: int = 0

    @property
    def per_call(self) -> float:
        """Mean seconds per call."""
        return self.seconds / max(self.calls, 1)

    @property
    def gflops(self) -> float:
        """Throughput in giga-flops per second."""
        if self.per_call <= 0:
            return 0.0
        return self.flops / self.per_call / 1e9


class Profiler:
    """Times named regions and accumulates their totals.

    Used as a context manager:

    ::

        with Profiler() as prof:
            with prof.region("forward"):
                loss = model(x)
            with prof.region("backward"):
                backward(loss)
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.records: dict[str, KernelRecord] = {}
        self._stack: list[tuple[str, float, int]] = []
        self.start_time = 0.0

    def __enter__(self) -> "Profiler":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.total_seconds = time.perf_counter() - self.start_time

    def region(self, name: str, flops: int = 0):
        """Return a context manager that times the region called ``name``."""
        return _Region(self, name, flops)

    def _record(self, name: str, seconds: float, flops: int) -> None:
        """Add one timing sample to the named region."""
        if not self.enabled:
            return
        existing = self.records.get(name)
        if existing is None:
            self.records[name] = KernelRecord(name=name, seconds=seconds, calls=1, flops=flops)
        else:
            existing.seconds += seconds
            existing.calls += 1
            existing.flops += flops

    def report(self, limit: int = 15) -> str:
        """Return a timing report sorted by total time."""
        if not self.records:
            return "no regions were timed"
        header = f"{'region':<28}{'calls':>7}{'total s':>12}{'per call ms':>13}{'GFLOP/s':>11}"
        lines = [header, "-" * len(header)]
        for record in sorted(self.records.values(), key=lambda r: -r.seconds)[:limit]:
            lines.append(
                f"{record.name:<28}{record.calls:>7}{record.seconds:>12.6f}"
                f"{record.per_call * 1e3:>13.3f}{record.gflops:>11.3f}"
            )
        return "\n".join(lines)

    def slowest(self) -> str | None:
        """Return the name of the region that took the most time."""
        if not self.records:
            return None
        return max(self.records.values(), key=lambda r: r.seconds).name

    def to_dict(self) -> dict[str, Any]:
        """Return the timings as a plain dictionary."""
        return {
            name: {
                "seconds": r.seconds,
                "calls": r.calls,
                "flops": r.flops,
                "gflops": r.gflops,
            }
            for name, r in self.records.items()
        }


class _Region:
    """Context manager returned by :meth:`Profiler.region`."""

    def __init__(self, profiler: Profiler, name: str, flops: int) -> None:
        self.profiler = profiler
        self.name = name
        self.flops = flops
        self.start = 0.0

    def __enter__(self) -> "_Region":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.profiler._record(self.name, time.perf_counter() - self.start, self.flops)


class AllocationTracker:
    """Counts tensor allocations and the bytes they hold.

    Wrapping a pass shows whether a change introduced extra buffers, which is
    usually the first thing that regresses in a memory-bound workload.
    """

    def __init__(self) -> None:
        self.count = 0
        self.bytes = 0
        self.peak_bytes = 0
        self._live = 0
        self._live_peak = 0
        self.by_shape: dict[str, int] = defaultdict(int)

    def record(self, tensor: Tensor) -> None:
        """Account for one allocation."""
        self.count += 1
        size = int(tensor.nbytes)
        self.bytes += size
        self._live += size
        self._live_peak = max(self._live_peak, self._live)
        self.peak_bytes = max(self.peak_bytes, self._live)
        self.by_shape[str(tuple(tensor.shape.dims))] += 1

    def release(self, tensor: Tensor) -> None:
        """Account for one buffer being released."""
        self._live = max(0, self._live - int(tensor.nbytes))

    def reset(self) -> None:
        """Clear all counters."""
        self.count = 0
        self.bytes = 0
        self.peak_bytes = 0
        self._live = 0
        self._live_peak = 0
        self.by_shape.clear()

    @property
    def average_bytes(self) -> float:
        """Mean allocation size in bytes."""
        return self.bytes / self.count if self.count else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the counters as a plain dictionary."""
        return {
            "allocations": self.count,
            "total_bytes": self.bytes,
            "average_bytes": self.average_bytes,
            "peak_live_bytes": self._live_peak,
            "distinct_shapes": len(self.by_shape),
        }

    def report(self) -> str:
        """Return a short allocation summary."""
        return "\n".join(
            [
                f"allocations     : {self.count}",
                f"total bytes     : {self.bytes}",
                f"average bytes   : {self.average_bytes:.1f}",
                f"peak live bytes : {self._live_peak}",
                f"distinct shapes : {len(self.by_shape)}",
            ]
        )


def estimate_bandwidth(tensor: Tensor, seconds: float) -> float:
    """Return the effective bandwidth of reading ``tensor`` in ``seconds``.

    Measured in bytes per second over the tensor's own size, which is the
    figure that tells you whether a kernel is bandwidth bound.
    """
    if seconds <= 0:
        return 0.0
    return float(tensor.nbytes) / seconds


def cache_efficiency(tensor: Tensor, working_set_bytes: int) -> float:
    """Return the fraction of a working set that a tensor occupies.

    A tensor larger than the working set cannot be held in cache, so every
    access streams from memory. Values above 1.0 mean it fits comfortably.
    """
    if working_set_bytes <= 0:
        return 0.0
    return float(tensor.nbytes) / working_set_bytes


def estimate_intensity(flops: int, bytes_moved: int) -> float:
    """Return arithmetic intensity in flops per byte.

    Above about one flop per byte a kernel is compute bound and worth
    optimizing with better math; below that it is bandwidth bound and worth
    optimizing with fewer or narrower accesses.
    """
    if bytes_moved <= 0:
        return 0.0
    return flops / bytes_moved


@dataclass
class BenchmarkResult:
    """The outcome of one benchmarked callable."""

    name: str
    seconds: float
    calls: int
    flops: int
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def per_call_ms(self) -> float:
        """Mean milliseconds per call."""
        return self.seconds / max(self.calls, 1) * 1e3

    @property
    def gflops(self) -> float:
        """Throughput in giga-flops per second."""
        total = self.seconds * max(self.calls, 1)
        return self.flops / total / 1e9 if total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a plain dictionary."""
        return {
            "name": self.name,
            "seconds": self.seconds,
            "calls": self.calls,
            "per_call_ms": self.per_call_ms,
            "flops": self.flops,
            "gflops": self.gflops,
            **self.extra,
        }


def benchmark(
    name: str,
    fn: Callable[[], Any],
    calls: int = 10,
    warmup: int = 1,
    flops: int = 0,
    **extra: Any,
) -> BenchmarkResult:
    """Time ``fn`` over ``calls`` iterations after ``warmup`` untimed ones.

    Warming up matters here because the first call pays for import-time setup
    and lazily created buffers, which would otherwise dominate a short run.
    """
    for _ in range(max(warmup, 0)):
        fn()
    start = time.perf_counter()
    for _ in range(max(calls, 1)):
        fn()
    seconds = time.perf_counter() - start
    return BenchmarkResult(name=name, seconds=seconds, calls=calls, flops=flops, extra=extra)


def compare(benchmarks: Sequence[BenchmarkResult], baseline: str) -> str:
    """Return a table comparing each benchmark against ``baseline``."""
    reference = next((b for b in benchmarks if b.name == baseline), None)
    header = f"{'benchmark':<28}{'per call ms':>13}{'GFLOP/s':>11}{'vs baseline':>14}"
    lines = [header, "-" * len(header)]
    for result in benchmarks:
        if reference is None or result is reference or reference.per_call_ms == 0:
            ratio = ""
        else:
            ratio = f"{result.per_call_ms / reference.per_call_ms:>13.2f}x"
        lines.append(f"{result.name:<28}{result.per_call_ms:>13.3f}{result.gflops:>11.3f}{ratio:>14}")
    return "\n".join(lines)
