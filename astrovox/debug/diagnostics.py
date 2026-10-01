"""Autograd diagnostics: the checks that make a silent failure loud.

Every function here answers one question that a falling loss curve cannot:

* :func:`gradient_consistency` -- is each gradient right, not just present?
* :func:`propagation_trace` -- how far does the backward path actually reach?
* :func:`verify_updates` -- did every parameter change, and if not why?
* :func:`gradient_distribution` -- what shape is the gradient, and is it healthy?
* :func:`validate_backward` -- did each backward use what its forward saved?
* :func:`validate_shapes` -- does every gradient match its operand?
* :func:`memory_report` -- what did the pass cost in memory?
* :func:`dashboard` -- all of it, in one block of text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

from astrovox.autograd.engine import grad_norm
from astrovox.autograd.function import GraphNode
from astrovox.autograd.gradients import check_gradients
from astrovox.autograd.graph import walk_from
from astrovox.tensor.tensor import Tensor


@dataclass
class ParameterGradientCheck:
    """The outcome of verifying one parameter's gradient numerically."""

    name: str
    passed: bool
    max_abs_error: float
    max_rel_error: float
    grad_norm: float
    elements: int
    norm_relative_error: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the check as a plain dictionary."""
        return {
            "name": self.name,
            "passed": self.passed,
            "max_abs_error": self.max_abs_error,
            "max_rel_error": self.max_rel_error,
            "norm_relative_error": self.norm_relative_error,
            "grad_norm": self.grad_norm,
            "elements": self.elements,
        }


def gradient_consistency(
    func: Any,
    module: Any,
    threshold: float = 1e-3,
    max_samples: int = 128,
) -> list[ParameterGradientCheck]:
    """Compare each parameter's analytical gradient to a finite difference.

    Args:
        func: zero-argument callable returning the scalar loss.
        module: the module whose parameters are checked.
        threshold: relative norm tolerance. The default suits float32, where
            a central difference carries roughly 1e-3 of rounding noise.
        max_samples: element positions sampled per parameter.

    Returns:
        One result per parameter, in the module's parameter order.
    """
    names = [name for name, _ in module.named_parameters()]
    params = list(module.parameters())
    results = check_gradients(func, params, rtol=threshold, atol=threshold, max_samples=max_samples)
    checks: list[ParameterGradientCheck] = []
    for name, param, result in zip(names, params, results):
        grad = param.grad
        norm = 0.0 if grad is None else float((grad.numpy().astype("float64") ** 2).sum() ** 0.5)
        # The per-element relative error is near 1 wherever the true gradient
        # is near zero, so the norm ratio is the figure worth reporting.
        scale = max(result.max_abs_error, 1e-30)
        checks.append(
            ParameterGradientCheck(
                name=name,
                passed=result.passed,
                max_abs_error=result.max_abs_error,
                max_rel_error=result.max_rel_error,
                grad_norm=norm,
                elements=result.num_elements,
                norm_relative_error=scale / max(norm, 1e-30),
            )
        )
    return checks


def format_consistency(checks: Sequence[ParameterGradientCheck]) -> str:
    """Render gradient consistency as an aligned report."""
    lines = [f"{'parameter':<44}{'status':<8}{'rel error':>12}{'grad norm':>13}"]
    lines.append("-" * len(lines[0]))
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(
            f"{check.name:<44}{status:<8}{check.norm_relative_error:>12.3e}{check.grad_norm:>13.5g}"
        )
    return "\n".join(lines)


def propagation_trace(outputs: Tensor | Sequence[Tensor]) -> str:
    """Render the graph as a tree, then the order backward visits it.

    The second half is the part that matters: if the backward stops early,
    the list of visited operations ends well before the first layer.
    """
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    nodes = list(walk_from(roots))
    order = sorted(nodes, key=lambda n: n.sequence_nr, reverse=True)

    # Plain ASCII: these reports are written to consoles and log files whose
    # encoding may not carry box-drawing characters.
    lines = ["forward graph (first recorded to last):"]
    for index, node in enumerate(reversed(order)):
        connector = "`--" if index == len(order) - 1 else "|--"
        lines.append(f"{connector} {node.name} #{node.sequence_nr}")
    lines.append("")
    lines.append("backward order (root first):")
    for step, node in enumerate(order, 1):
        lines.append(f"  {step:3d}. [ok] {node.name} #{node.sequence_nr}")
    lines.append(f"  reached {len(order)} of {len(nodes)} recorded operations")
    return "\n".join(lines)


def propagation_depth(outputs: Tensor | Sequence[Tensor]) -> int:
    """Return the longest chain of operations between a leaf and a root."""
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    by_id: dict[int, GraphNode] = {id(n): n for n in walk_from(roots)}

    def depth(node: GraphNode, seen: frozenset[int] = frozenset()) -> int:
        if id(node) in seen:
            return 0
        seen = seen | {id(node)}
        best = 0
        for parent, _ in node.next_functions:
            if parent is not None and id(parent) in by_id:
                best = max(best, 1 + depth(parent, seen))
        return best

    return max((depth(n) for n in by_id.values()), default=0)


@dataclass
class UpdateStatus:
    """Whether one parameter actually changed during an optimizer step."""

    name: str
    updated: bool
    delta_norm: float
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the status as a plain dictionary."""
        return {
            "name": self.name,
            "updated": self.updated,
            "delta_norm": self.delta_norm,
            "reason": self.reason,
        }


def verify_updates(module: Any, before: dict[str, Tensor], tol: float = 0.0) -> list[UpdateStatus]:
    """Report which parameters changed since the snapshot ``before``.

    A parameter that did not move is either frozen by a zero gradient or was
    excluded from the optimizer; the reason distinguishes the two.
    """
    statuses: list[UpdateStatus] = []
    for name, param in module.named_parameters():
        old = before.get(name)
        if old is None:
            statuses.append(UpdateStatus(name, False, 0.0, "not in snapshot"))
            continue
        delta = float(((param.numpy() - old.numpy()).astype("float64") ** 2).sum() ** 0.5)
        if delta > tol:
            statuses.append(UpdateStatus(name, True, delta))
            continue
        grad = param.grad
        if grad is None:
            reason = "no gradient was computed"
        elif not np.any(grad.numpy() != 0.0):
            reason = "gradient is exactly zero"
        else:
            reason = "gradient was nonzero but the step did not move it (check the learning rate)"
        statuses.append(UpdateStatus(name, False, delta, reason))
    return statuses


def format_updates(statuses: Sequence[UpdateStatus]) -> str:
    """Render update verification as an aligned report."""
    lines = [f"{'parameter':<44}{'updated':<10}{'delta':>12}  detail"]
    lines.append("-" * len(lines[0]))
    for status in statuses:
        mark = "yes" if status.updated else "NO"
        lines.append(
            f"{status.name:<44}{mark:<10}{status.delta_norm:>12.4g}  {status.reason}"
        )
    return "\n".join(lines)


@dataclass
class Distribution:
    """Summary statistics for one gradient."""

    name: str
    minimum: float
    maximum: float
    mean: float
    std: float
    l2_norm: float
    zero_fraction: float
    nan_fraction: float
    inf_fraction: float

    @property
    def healthy(self) -> bool:
        """True when the gradient contains no NaN and no infinity."""
        return self.nan_fraction == 0.0 and self.inf_fraction == 0.0

    def to_dict(self) -> dict[str, Any]:
        """Return the distribution as a plain dictionary."""
        return {
            "name": self.name,
            "min": self.minimum,
            "max": self.maximum,
            "mean": self.mean,
            "std": self.std,
            "l2_norm": self.l2_norm,
            "zero_pct": self.zero_fraction * 100.0,
            "nan_pct": self.nan_fraction * 100.0,
            "inf_pct": self.inf_fraction * 100.0,
        }


def gradient_distribution(module: Any) -> list[Distribution]:
    """Return min, max, mean, std, norm, and unhealthy-value fractions per gradient."""
    out: list[Distribution] = []
    for name, param in module.named_parameters():
        grad = param.grad
        if grad is None:
            out.append(Distribution(name, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0))
            continue
        values = grad.numpy().astype("float64")
        finite = values[np.isfinite(values)]
        count = values.size or 1
        out.append(
            Distribution(
                name=name,
                minimum=float(finite.min()) if finite.size else 0.0,
                maximum=float(finite.max()) if finite.size else 0.0,
                mean=float(finite.mean()) if finite.size else 0.0,
                std=float(finite.std()) if finite.size else 0.0,
                l2_norm=float((values**2).sum() ** 0.5),
                zero_fraction=float((values == 0.0).sum()) / count,
                nan_fraction=float(np.isnan(values).sum()) / count,
                inf_fraction=float(np.isinf(values).sum()) / count,
            )
        )
    return out


def format_distribution(dists: Sequence[Distribution]) -> str:
    """Render gradient distributions as an aligned table."""
    header = (
        f"{'parameter':<34}{'min':>10}{'max':>10}{'mean':>10}{'std':>10}"
        f"{'l2':>11}{'zero%':>8}{'nan%':>7}{'inf%':>7}"
    )
    lines = [header, "-" * len(header)]
    for d in dists:
        lines.append(
            f"{d.name:<34}{d.minimum:>10.4g}{d.maximum:>10.4g}{d.mean:>10.4g}"
            f"{d.std:>10.4g}{d.l2_norm:>11.4g}{d.zero_fraction * 100:>8.1f}"
            f"{d.nan_fraction * 100:>7.1f}{d.inf_fraction * 100:>7.1f}"
        )
    return "\n".join(lines)


def validate_shapes(outputs: Tensor | Sequence[Tensor]) -> list[str]:
    """Check that each node's gradient shape matches the operand it belongs to.

    A mismatch here is the signature of a backward that reshapes wrongly, which
    is otherwise silent until the values turn out to be permuted.
    """
    from astrovox.autograd.engine import _ENGINE

    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    problems: list[str] = []

    original = _ENGINE.backward

    def spy(out, grad_outputs=None, retain_graph=False):
        result = original(out, grad_outputs, retain_graph)
        for node in walk_from([out] if isinstance(out, Tensor) else out):
            for position, value in enumerate(node.inputs):
                if not isinstance(value, Tensor) or value.grad is None:
                    continue
                if value.grad.shape != value.shape:
                    problems.append(
                        f"{node.name} produced a gradient of shape "
                        f"{tuple(value.grad.shape.dims)} for an input of shape "
                        f"{tuple(value.shape.dims)}"
                    )
        return result

    _ENGINE.backward = spy
    try:
        for root in roots:
            spy(root)
    finally:
        _ENGINE.backward = original
    return problems


def validate_backward(outputs: Tensor | Sequence[Tensor]) -> list[str]:
    """Report saved tensors that the backward pass never read.

    The engine's real backward is instrumented rather than simulated, so the
    result reflects the code that actually runs. That backward accumulates
    gradients as a side effect, which is usually what the caller wants anyway;
    call ``zero_grad`` first if a clean slate matters.
    """
    from astrovox.autograd import backward

    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    nodes = list(walk_from(roots))

    # Clearing the recorders first means the report describes only this pass.
    for node in nodes:
        node.ctx.used.clear()

    for root in roots:
        if isinstance(root, Tensor) and root._grad_fn is not None:
            backward(root)

    problems: list[str] = []
    for node in nodes:
        saved = {
            key
            for key, value in getattr(node.ctx, "saved", {}).items()
            if isinstance(value, Tensor)
        }
        unused = saved - node.ctx.used
        if unused:
            problems.append(
                f"{node.name} saved {sorted(unused)} but its backward never read it"
            )
    return problems


@dataclass
class MemoryReport:
    """Memory accounting for a forward and backward pass.

    ``saved_bytes`` is the interesting figure: it is what stays resident
    between forward and backward, so it is the peak footprint of a training
    step for this graph.
    """

    active_tensors: int = 0
    saved_tensors: int = 0
    saved_bytes: int = 0
    live_bytes: int = 0
    peak_bytes: int = 0
    temporaries: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a plain dictionary."""
        return {
            "active_tensors": self.active_tensors,
            "saved_tensors": self.saved_tensors,
            "saved_bytes": self.saved_bytes,
            "live_bytes": self.live_bytes,
            "peak_bytes": self.peak_bytes,
            "temporaries": self.temporaries,
        }


def memory_report(outputs: Tensor | Sequence[Tensor]) -> MemoryReport:
    """Account for what the graph holds between forward and backward."""
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    nodes = list(walk_from(roots))

    saved_tensors = 0
    saved_bytes = 0
    live_bytes = 0
    seen: set[int] = set()
    for node in nodes:
        for value in getattr(node.ctx, "saved", {}).values():
            if isinstance(value, Tensor) and id(value) not in seen:
                seen.add(id(value))
                saved_tensors += 1
                saved_bytes += int(value.nbytes)
        for value in node.outputs:
            if isinstance(value, Tensor) and id(value) not in seen:
                seen.add(id(value))
                live_bytes += int(value.nbytes)

    return MemoryReport(
        active_tensors=len(seen),
        saved_tensors=saved_tensors,
        saved_bytes=saved_bytes,
        live_bytes=live_bytes,
        peak_bytes=saved_bytes + live_bytes,
        temporaries=sum(1 for n in nodes if n.name == "view"),
    )


def format_memory(report: MemoryReport) -> str:
    """Render the memory report as a short block of text."""
    return "\n".join(
        [
            f"active tensors : {report.active_tensors}",
            f"saved tensors  : {report.saved_tensors}",
            f"saved bytes    : {_mb(report.saved_bytes)}",
            f"live bytes     : {_mb(report.live_bytes)}",
            f"peak bytes     : {_mb(report.peak_bytes)}",
            f"view temporaries: {report.temporaries}",
        ]
    )


def _mb(value: int) -> str:
    """Format a byte count as megabytes."""
    return f"{value / (1024 * 1024):.2f} MB"


@dataclass
class Dashboard:
    """The combined result of every autograd check."""

    graph_nodes: int
    trainable_params: int
    longest_chain: int
    memory: MemoryReport
    checks: list[ParameterGradientCheck]
    distributions: list[Distribution]
    dead_parameters: list[str] = field(default_factory=list)
    zero_gradients: list[str] = field(default_factory=list)
    nan_gradients: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        """True when nothing failed and no gradient is dead or non-finite."""
        return (
            self.problems == []
            and all(c.passed for c in self.checks)
            and not self.dead_parameters
            and not self.nan_gradients
        )

    def render(self) -> str:
        """Return the dashboard as a boxed text report."""
        bar = "=" * 61
        rule = "-" * 61
        passed = sum(1 for c in self.checks if c.passed)
        failed = len(self.checks) - passed
        lines = [
            bar,
            "ASTROVOX AUTOGRAD REPORT".center(61),
            bar,
            f"Graph Nodes         : {self.graph_nodes}",
            f"Trainable Params    : {self.trainable_params}",
            f"Longest Chain       : {self.longest_chain} ops",
            "",
            "Gradient Check",
            rule,
            f"Passed             : {passed}",
            f"Failed             : {failed}",
            "",
            f"Dead Parameters    : {len(self.dead_parameters)}",
            f"Zero Gradients     : {len(self.zero_gradients)}",
            f"NaN Gradients      : {len(self.nan_gradients)}",
            "",
            "Memory",
            rule,
            f"Peak Memory        : {_mb(self.memory.peak_bytes)}",
            f"Saved Tensors      : {self.memory.saved_tensors}",
            "",
            "Overall Status",
            rule,
            "HEALTHY" if self.healthy else "ATTENTION NEEDED",
            bar,
        ]
        if self.problems:
            lines.append("")
            for problem in self.problems:
                lines.append(f"  ! {problem}")
        return "\n".join(lines)


def dashboard(
    outputs: Tensor | Sequence[Tensor],
    module: Any,
    checks: Sequence[ParameterGradientCheck] | None = None,
    run_backward: bool = True,
) -> Dashboard:
    """Run every check and combine the results into one report.

    The graph is retained for the duration so that structural facts (node
    count, chain depth, memory) and gradient facts can be reported together: a
    plain ``backward`` releases the graph, which would leave the first two
    empty and make the report look healthy for the wrong reason.
    """
    from astrovox.autograd import backward
    from astrovox.debug.inspector import inspect

    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)

    # Structural facts are read while the graph is intact.
    report = inspect(roots, module)
    depth = propagation_depth(roots)
    memory = memory_report(roots)

    if run_backward and checks is None:
        for param in module.parameters():
            param._grad = None
        for root in roots:
            if isinstance(root, Tensor) and root._grad_fn is not None:
                backward(root, retain_graph=True)
    elif run_backward:
        for param in module.parameters():
            param._grad = None
        for root in roots:
            if isinstance(root, Tensor) and root._grad_fn is not None:
                backward(root, retain_graph=True)

    dists = gradient_distribution(module)

    dead = [name for name, info in report.parameters.items() if not info["has_grad"]]
    zero = [d.name for d in dists if d.l2_norm == 0.0]
    nan = [d.name for d in dists if not d.healthy]

    problems: list[str] = []
    if dead:
        problems.append(f"{len(dead)} parameter(s) never received a gradient: {', '.join(dead)}")
    if nan:
        problems.append(f"{len(nan)} gradient(s) contain NaN or infinity: {', '.join(nan)}")
    problems.extend(validate_shapes(roots))
    for check in checks or []:
        if not check.passed:
            problems.append(
                f"gradient check failed for {check.name} "
                f"(relative error {check.norm_relative_error:.3e})"
            )

    return Dashboard(
        graph_nodes=report.node_count,
        trainable_params=len(report.parameters),
        longest_chain=depth,
        memory=memory,
        checks=list(checks or []),
        distributions=dists,
        dead_parameters=dead,
        zero_gradients=zero,
        nan_gradients=nan,
        problems=problems,
    )
