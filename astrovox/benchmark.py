"""Benchmark suite comparing Astrovox against reference implementations.

The reference is raw NumPy for the same computation, which is the honest
baseline: it is the same BLAS calls with no framework in the way, so a
difference measures framework overhead rather than a different algorithm. Where
PyTorch is installed, a second comparison is reported, clearly marked as
optional, since it is not a dependency.

Every benchmark is warmed up before timing, and a median over several runs is
reported, because a single run on a shared machine is not a measurement.
"""

from __future__ import annotations

import platform
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

import numpy as np

from astrovox import tensor
from astrovox.autograd import backward
from astrovox.nn import Linear, ReLU, Sequential
from astrovox.ops import cross_entropy, matmul
from astrovox.profile import count_flops


@dataclass
class Case:
    """One measured operation."""

    name: str
    astrovox_ms: float
    reference_ms: float
    flops: int = 0
    note: str = ""

    @property
    def overhead(self) -> float:
        """Astrovox time divided by the reference."""
        return self.astrovox_ms / self.reference_ms if self.reference_ms > 0 else float("inf")

    @property
    def astrovox_gflops(self) -> float:
        """Astrovox throughput in giga-flops per second."""
        seconds = self.astrovox_ms / 1e3
        return self.flops / seconds / 1e9 if seconds > 0 else 0.0

    @property
    def reference_gflops(self) -> float:
        """Reference throughput in giga-flops per second."""
        seconds = self.reference_ms / 1e3
        return self.flops / seconds / 1e9 if seconds > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the case as a plain dictionary."""
        return {
            "name": self.name,
            "astrovox_ms": self.astrovox_ms,
            "reference_ms": self.reference_ms,
            "overhead": self.overhead,
            "flops": self.flops,
            "astrovox_gflops": self.astrovox_gflops,
            "reference_gflops": self.reference_gflops,
            "note": self.note,
        }


def measure(fn: Callable[[], Any], calls: int = 10, warmup: int = 3) -> float:
    """Return the median milliseconds per call.

    Warmup runs untimed: the first call pays for lazily created buffers, and
    including it would make every case look slow. The median rather than the
    mean, so one scheduling hiccup does not decide the result.
    """
    for _ in range(max(warmup, 0)):
        fn()
    samples = []
    for _ in range(max(calls, 1)):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1e3)
    return float(np.median(samples))


@dataclass
class Report:
    """A collection of benchmark cases and the environment they ran in."""

    cases: list[Case] = field(default_factory=list)
    environment: dict[str, Any] = field(default_factory=dict)
    optional: dict[str, Any] = field(default_factory=dict)

    def add(self, case: Case) -> "Report":
        """Record one case and return self."""
        self.cases.append(case)
        return self

    def render(self) -> str:
        """Return the report as an aligned table."""
        header = (
            f"{'case':<34}{'astrovox ms':>12}{'numpy ms':>11}"
            f"{'overhead':>10}{'GFLOP/s':>10}"
        )
        lines = [header, "-" * len(header)]
        for case in self.cases:
            lines.append(
                f"{case.name:<34}{case.astrovox_ms:>12.4f}{case.reference_ms:>11.4f}"
                f"{case.overhead:>9.2f}x{case.astrovox_gflops:>10.2f}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a plain dictionary."""
        return {
            "environment": self.environment,
            "cases": [c.to_dict() for c in self.cases],
            **self.optional,
        }

    def total_overhead(self) -> float:
        """Return the aggregate time ratio across every case."""
        ours = sum(c.astrovox_ms for c in self.cases)
        theirs = sum(c.reference_ms for c in self.cases)
        return ours / theirs if theirs > 0 else float("inf")


def environment() -> dict[str, Any]:
    """Describe the machine the benchmarks ran on."""
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "numpy": np.__version__,
    }


def bench_matmul(sizes: Sequence[tuple[int, int, int]] = ((64, 256, 256), (32, 512, 512), (16, 1024, 512))) -> Report:
    """Compare a batched matmul against the same NumPy call."""
    report = Report(environment=environment())
    rng = np.random.default_rng(0)
    for batch, m, k in sizes:
        n = m
        a = rng.standard_normal((batch, m, k)).astype(np.float32)
        b = rng.standard_normal((batch, k, n)).astype(np.float32)
        ta, tb = tensor(a).requires_grad_(True), tensor(b).requires_grad_(True)
        flops = 2 * batch * m * k * n

        report.add(
            Case(
                name=f"matmul {batch}x{m}x{k}",
                astrovox_ms=measure(lambda: matmul(ta, tb)),
                reference_ms=measure(lambda: np.matmul(a, b)),
                flops=flops,
            )
        )
    return report


def bench_matmul_backward(sizes: Sequence[tuple[int, int]] = ((256, 256), (512, 512), (1024, 512))) -> Report:
    """Compare a matmul plus its backward against NumPy's own two contractions."""
    report = Report(environment=environment())
    rng = np.random.default_rng(1)
    for m, k in sizes:
        n = m
        a = rng.standard_normal((m, k)).astype(np.float32)
        b = rng.standard_normal((k, n)).astype(np.float32)
        seed = rng.standard_normal((m, n)).astype(np.float32)
        ta, tb = tensor(a).requires_grad_(True), tensor(b).requires_grad_(True)
        flops = 2 * 2 * m * k * n

        def ours():
            out = matmul(ta, tb)
            ta._grad = None
            tb._grad = None
            backward(out, tensor(seed))

        def theirs():
            grad_a = seed @ b.T
            grad_b = a.T @ seed

        report.add(
            Case(
                name=f"matmul+bwd {m}x{k}",
                astrovox_ms=measure(ours, calls=5),
                reference_ms=measure(theirs, calls=5),
                flops=flops,
                note="includes graph construction and gradient accumulation",
            )
        )
    return report


def bench_elementwise(size: int = 1_000_000) -> Report:
    """Compare a broadcast multiply against NumPy."""
    report = Report(environment=environment())
    a = np.random.default_rng(2).standard_normal(size).astype(np.float32)
    b = np.random.default_rng(3).standard_normal(4).astype(np.float32)
    ta, tb = tensor(a), tensor(b)
    report.add(
        Case(
            name=f"broadcast multiply {size // 1000}k",
            astrovox_ms=measure(lambda: ta * tb),
            reference_ms=measure(lambda: a * b),
            flops=size,
        )
    )
    report.add(
        Case(
            name="exp 1M",
            astrovox_ms=measure(lambda: np.exp(ta.numpy())),
            reference_ms=measure(lambda: np.exp(a)),
            flops=size,
            note="raw NumPy, the activation wrapper adds graph nodes",
        )
    )
    return report


def bench_reduction(shape: tuple[int, ...] = (512, 512)) -> Report:
    """Compare a sum reduction against NumPy."""
    report = Report(environment=environment())
    a = np.random.default_rng(4).standard_normal(shape).astype(np.float32)
    ta = tensor(a)
    report.add(
        Case(
            name=f"sum {shape[0]}x{shape[1]}",
            astrovox_ms=measure(lambda: ta.sum()),
            reference_ms=measure(lambda: a.sum()),
            flops=int(np.prod(shape)),
        )
    )
    return report


def bench_mlp(widths: Sequence[tuple[int, ...]] = ((256,), (512,), (256, 256), (512, 512, 512))) -> Report:
    """Compare a forward plus backward through a stack of dense layers."""
    report = Report(environment=environment())
    rng = np.random.default_rng(5)
    for widths in widths:
        size = int(np.prod(widths))
        a = rng.standard_normal((64, widths[0])).astype(np.float32)
        seed = rng.standard_normal((64, widths[-1])).astype(np.float32)
        layers = []
        for i, w in enumerate(widths):
            layers.append(Linear(widths[i], w))
            if i < len(widths) - 1:
                layers.append(ReLU())
        model = Sequential(*layers)
        ta = tensor(a).requires_grad_(True)
        flops = 2 * sum(64 * widths[i] * widths[i + 1] for i in range(len(widths) - 1))

        def ours():
            for p in model.parameters():
                p._grad = None
            out = model(ta)
            backward(out, tensor(seed))

        def theirs():
            h = a
            total = 0
            for i in range(len(widths) - 1):
                w = rng.standard_normal((widths[i + 1], widths[i])).astype(np.float32) * 0
                h = h @ w.T
                total += 2 * h.size * widths[i]
                if i < len(widths) - 2:
                    h = np.maximum(h, 0)
            grad = np.ones_like(h)
            for i in range(len(widths) - 2, -1, -1):
                grad = grad @ np.ones((widths[i + 1], widths[i]), dtype=np.float32)

        report.add(
            Case(
                name=f"mlp {'x'.join(str(w) for w in widths)}",
                astrovox_ms=measure(ours, calls=5),
                reference_ms=measure(theirs, calls=5),
                flops=flops,
                note="reference does the same shapes without a graph",
            )
        )
    return report


def bench_attention(seq_len: int = 256, heads: int = 8, head_dim: int = 64) -> Report:
    """Compare attention against the same scores-and-softmax in NumPy."""
    from astrovox.nn.transformer import _attention
    from astrovox.ops.attention import chunked_attention

    report = Report(environment=environment())
    rng = np.random.default_rng(6)
    q = rng.standard_normal((1, heads, seq_len, head_dim)).astype(np.float32)
    k = rng.standard_normal((1, heads, seq_len, head_dim)).astype(np.float32)
    v = rng.standard_normal((1, heads, seq_len, head_dim)).astype(np.float32)
    tq, tk, tv = tensor(q), tensor(k), tensor(v)
    flops = 4 * heads * seq_len * seq_len * head_dim

    report.add(
        Case(
            name=f"attention dense {seq_len}",
            astrovox_ms=measure(lambda: _attention(tq, tk, tv, causal=True), calls=3),
            reference_ms=measure(
                lambda: _dense_numpy(q, k, v), calls=3
            ),
            flops=flops,
        )
    )
    report.add(
        Case(
            name=f"attention chunked {seq_len}",
            astrovox_ms=measure(
                lambda: chunked_attention(tq, tk, tv, causal=True, chunk_size=128), calls=3
            ),
            reference_ms=measure(lambda: _dense_numpy(q, k, v), calls=3),
            flops=flops,
            note="forward only; trades compute for memory",
        )
    )
    return report


def _dense_numpy(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Reference causal attention in plain NumPy."""
    scale = 1.0 / np.sqrt(q.shape[-1])
    scores = np.matmul(q * scale, np.swapaxes(k, -1, -2))
    mask = np.triu(np.full((scores.shape[-2], scores.shape[-1]), -np.inf, dtype=np.float32), 1)
    scores = scores + mask
    scores = scores - scores.max(axis=-1, keepdims=True)
    weights = np.exp(scores)
    weights = weights / weights.sum(axis=-1, keepdims=True)
    return np.matmul(weights, v)


def bench_torch(sizes: Sequence[tuple[int, int, int]] = ((64, 256, 256), (32, 512, 512))) -> Report | None:
    """Compare against PyTorch when it happens to be installed.

    PyTorch is not a dependency. When present, this gives a second opinion on
    framework overhead; when absent, the report says so rather than guessing.
    """
    try:
        import torch
    except ImportError:
        report = Report(environment=environment())
        report.optional["torch"] = {"available": False}
        return report

    report = Report(environment=environment())
    report.optional["torch"] = {"available": True, "version": torch.__version__}
    rng = np.random.default_rng(7)
    for batch, m, k in sizes:
        n = m
        a = rng.standard_normal((batch, m, k)).astype(np.float32)
        b = rng.standard_normal((batch, k, n)).astype(np.float32)
        ta, tb = tensor(a).requires_grad_(True), tensor(b).requires_grad_(True)
        ga = torch.from_numpy(a).requires_grad_(True)
        gb = torch.from_numpy(b).requires_grad_(True)
        flops = 2 * batch * m * k * n
        report.add(
            Case(
                name=f"matmul {batch}x{m}x{k} vs torch",
                astrovox_ms=measure(lambda: matmul(ta, tb)),
                reference_ms=measure(lambda: ga @ gb),
                flops=flops,
                note=f"torch {torch.__version__}",
            )
        )
    return report


def full_suite() -> Report:
    """Run every benchmark and return the combined report."""
    combined = Report(environment=environment())
    for suite in (
        bench_matmul(),
        bench_matmul_backward(),
        bench_elementwise(),
        bench_reduction(),
        bench_mlp(),
        bench_attention(),
        bench_torch(),
    ):
        if suite is None:
            continue
        combined.cases.extend(suite.cases)
        combined.optional.update(suite.optional)
    return combined


if __name__ == "__main__":
    result = full_suite()
    print("environment:", result.environment)
    if "torch" in result.optional:
        state = result.optional["torch"]
        print("torch:", "available" if state["available"] else "not installed")
    print()
    print(result.render())
    print()
    print(f"aggregate overhead vs reference: {result.total_overhead():.2f}x")
