"""Gradient utilities: access, zeroing, and numerical verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np

from astrovox.tensor.shape import Shape
from astrovox.tensor.tensor import Tensor


@dataclass
class GradientCheckResult:
    """Outcome of comparing analytical and numerical gradients."""

    passed: bool
    max_abs_error: float
    max_rel_error: float
    num_elements: int
    failing_indices: list[tuple[int, ...]]

    def to_dict(self) -> dict[str, object]:
        """Return the result as a plain dictionary."""
        return {
            "passed": self.passed,
            "max_abs_error": self.max_abs_error,
            "max_rel_error": self.max_rel_error,
            "num_elements": self.num_elements,
            "failing_indices": self.failing_indices[:10],
        }

    def __str__(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"GradientCheck {verdict}: max_abs_error={self.max_abs_error:.3e} "
            f"max_rel_error={self.max_rel_error:.3e} over {self.num_elements} elements"
        )


def numerical_gradient(
    func: "callable[[], Tensor]",
    tensor: Tensor,
    eps: float = 1e-5,
    indices: Sequence[tuple[int, ...]] | None = None,
) -> Tensor:
    """Estimate the gradient of a scalar ``func`` with central differences.

    Args:
        func: zero-argument callable returning a scalar tensor.
        tensor: the tensor to differentiate.
        eps: perturbation size.
        indices: specific positions to sample; defaults to every element.
    """
    positions = indices if indices is not None else list(_all_indices(tensor.shape))
    out = Tensor.zeros((len(positions),), tensor.dtype, tensor.device)
    values = out.numpy()
    original = tensor.numpy().copy()

    for slot, index in enumerate(positions):
        tensor.numpy()[index] = original[index] + eps
        plus = float(func().item())
        tensor.numpy()[index] = original[index] - eps
        minus = float(func().item())
        tensor.numpy()[index] = original[index]
        values[slot] = (plus - minus) / (2 * eps)
    return out


def check_gradients(
    func: "callable[[], Tensor]",
    tensors: Sequence[Tensor],
    eps: float = 1e-3,
    rtol: float = 1e-2,
    atol: float = 1e-3,
    max_samples: int | None = 512,
) -> list[GradientCheckResult]:
    """Compare analytical and numerical gradients for each tensor in ``tensors``.

    ``func`` must return a scalar tensor and must use the same tensor objects
    so that the analytical gradients land on them.

    The default ``eps`` suits single precision: in float32 a central
    difference carries roughly 1e-3 relative noise, so a tiny step would
    measure that noise rather than the derivative.

    A sample passes when ``|analytical - numerical| <= atol + rtol *
    |numerical|``. Combining the tolerances matters because the relative error
    is undefined near a zero gradient, where the absolute error must decide.
    """
    results: list[GradientCheckResult] = []
    for t in tensors:
        if t.grad is not None:
            t._grad = None

        out = func()
        if out.grad is None and getattr(out, "_grad_fn", None) is not None:
            from astrovox.autograd.engine import backward

            backward(out)

        analytical = t.grad
        if analytical is None:
            results.append(GradientCheckResult(False, float("inf"), float("inf"), 0, []))
            continue

        positions = list(_all_indices(t.shape))
        if max_samples is not None and len(positions) > max_samples:
            positions = _sample_positions(positions, max_samples)

        numerical = numerical_gradient(func, t, eps=eps, indices=positions)
        flat_grad = analytical.contiguous().reshape(-1).numpy()
        # Resolve each sampled position to its flat offset using the tensor's
        # own shape, so subsampling cannot misalign the comparison.
        offsets = [t.shape.ravel(p) for p in positions]
        got = flat_grad[offsets]
        expected = numerical.numpy()

        abs_error = np.abs(got - expected)
        denom = np.maximum(np.abs(got) + np.abs(expected), 1e-12)
        rel_error = abs_error / denom
        tolerance = atol + rtol * np.abs(expected)

        failing = [p for p, a, tol in zip(positions, abs_error, tolerance) if a > tol]
        results.append(
            GradientCheckResult(
                passed=not failing,
                max_abs_error=float(abs_error.max()) if abs_error.size else 0.0,
                max_rel_error=float(rel_error.max()) if rel_error.size else 0.0,
                num_elements=len(positions),
                failing_indices=failing,
            )
        )
    return results


def zero_grad(tensors: Iterable[Tensor]) -> None:
    """Clear accumulated gradients on ``tensors``."""
    for t in tensors:
        if t is not None:
            t._grad = None


def zero_grad_module(module: object) -> None:
    """Clear accumulated gradients on every parameter of ``module``."""
    zero_grad(module.parameters())  # type: ignore[attr-defined]


def has_gradients(module: object) -> bool:
    """Return whether any parameter of ``module`` currently holds a gradient."""
    return any(p.grad is not None for p in module.parameters())  # type: ignore[attr-defined]


def gradient_map(module: object, prefix: str = "") -> dict[str, Tensor]:
    """Return ``{name: gradient}`` for every parameter of ``module``."""
    out: dict[str, Tensor] = {}
    for name, param in module.named_parameters():  # type: ignore[attr-defined]
        if param.grad is not None:
            out[f"{prefix}{name}"] = param.grad
    return out


def flatten_gradients(tensors: Sequence[Tensor]) -> Tensor:
    """Concatenate ``tensors`` into a single 1-D gradient vector."""
    if not tensors:
        return Tensor.zeros((0,))
    total = sum(t.numel for t in tensors)
    out = Tensor.zeros((total,), tensors[0].dtype, tensors[0].device)
    offset = 0
    for t in tensors:
        flat = t.contiguous().reshape(-1)
        out.numpy()[offset : offset + flat.numel] = flat.numpy()
        offset += flat.numel
    return out


def _all_indices(shape: Shape) -> Iterable[tuple[int, ...]]:
    """Yield every index tuple of ``shape``."""
    from itertools import product

    return product(*(range(d) for d in shape.dims))


def _sample_positions(
    positions: Sequence[tuple[int, ...]], count: int, seed: int = 0
) -> list[tuple[int, ...]]:
    """Deterministically subsample ``positions`` down to ``count`` entries."""
    if len(positions) <= count:
        return list(positions)
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(positions), size=count, replace=False)
    return [positions[i] for i in sorted(chosen)]


def gradcheck(
    func: "callable[[], Tensor]",
    tensors: Sequence[Tensor],
    **kwargs: object,
) -> bool:
    """Return whether every gradient passes the numerical comparison."""
    return all(r.passed for r in check_gradients(func, tensors, **kwargs))  # type: ignore[arg-type]
