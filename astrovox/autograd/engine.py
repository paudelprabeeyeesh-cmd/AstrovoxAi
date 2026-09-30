"""Reverse-mode automatic differentiation.

The engine walks the graph in reverse topological order. Because graph nodes
record a monotonically increasing sequence number at creation time, sorting
descending by that number yields a valid evaluation order without needing an
explicit topological sort, and it visits every node exactly once even when
subgraphs are shared.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from astrovox.autograd.function import GraphNode
from astrovox.autograd.graph import GraphContext, free_graph, walk_from
from astrovox.tensor.tensor import Tensor


@dataclass
class BackwardResult:
    """Summary of one backward pass."""

    nodes_executed: int = 0
    leaves_with_grad: int = 0
    grad_norm: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """Return the summary as a plain dictionary."""
        return {
            "nodes_executed": self.nodes_executed,
            "leaves_with_grad": self.leaves_with_grad,
            "grad_norm": round(self.grad_norm, 6),
        }


class Engine:
    """Executes reverse-mode differentiation.

    The engine holds no state between passes beyond its counters, so a single
    instance can serve an entire training loop.
    """

    def __init__(self) -> None:
        self.nodes_executed = 0
        self.last_result = BackwardResult()

    def backward(
        self,
        outputs: Tensor | Sequence[Tensor],
        grad_outputs: Tensor | Sequence[Tensor] | None = None,
        retain_graph: bool | None = None,
    ) -> BackwardResult:
        """Differentiate ``outputs`` with respect to every reachable leaf.

        Args:
            outputs: one or more tensors to differentiate. Each must be a
                scalar unless ``grad_outputs`` supplies its seed.
            grad_outputs: seeds for the output gradients; defaults to ones.
            retain_graph: keep the graph for a further backward pass. Defaults
                to the ambient :class:`GraphContext` setting.

        Raises:
            ValueError: if a non-scalar output has no explicit seed.
        """
        roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
        keep = GraphContext.retain_graph() if retain_graph is None else bool(retain_graph)
        seeds = self._resolve_seeds(roots, grad_outputs)

        # Node sequence numbers are assigned on creation, so descending order
        # guarantees every producer is visited before any of its consumers.
        nodes = sorted(walk_from(roots), key=lambda n: n.sequence_nr, reverse=True)

        # Accumulate each node's incoming gradients from all its consumers.
        incoming: dict[int, list[Tensor]] = defaultdict(list)
        for index, (root, seed) in enumerate(zip(roots, seeds)):
            node = getattr(root, "_grad_fn", None)
            if node is not None:
                incoming[id(node)].append(seed)

        result = BackwardResult()
        leaves: dict[int, Tensor] = {}

        for node in nodes:
            contributions = incoming.get(id(node))
            if not contributions:
                continue
            grad_output = contributions[0] if len(contributions) == 1 else _sum_tensors(contributions)
            # A node's backward receives a gradient shaped like its own output.
            grad_output = _align_to_outputs(node, grad_output)

            try:
                grads = node.function.backward(node.ctx, grad_output)
            except NotImplementedError:
                grads = None
            if grads is None:
                continue

            result.nodes_executed += 1
            for position, grad in enumerate(grads):
                if grad is None or position >= len(node.next_functions):
                    continue
                # The gradient at ``position`` belongs to ``node.inputs[position]``,
                # so that is the shape it must be aligned to. The producing
                # node is what the gradient is forwarded to.
                source = node.inputs[position]
                parent, _ = node.next_functions[position]
                if parent is None:
                    if isinstance(source, Tensor) and source.requires_grad:
                        source._grad = grad if source._grad is None else source._grad + grad
                        leaves[id(source)] = source
                elif isinstance(source, Tensor):
                    incoming[id(parent)].append(_broadcast_like(grad, source))

        result.leaves_with_grad = len(leaves)
        result.grad_norm = grad_norm(leaves.values())
        self.nodes_executed += result.nodes_executed
        self.last_result = result

        if not keep:
            free_graph(roots)
        return result

    def _resolve_seeds(
        self,
        roots: Sequence[Tensor],
        grad_outputs: Tensor | Sequence[Tensor] | None,
    ) -> list[Tensor]:
        """Return the gradient seed for each root tensor."""
        if grad_outputs is not None:
            provided = [grad_outputs] if isinstance(grad_outputs, Tensor) else list(grad_outputs)
            if len(provided) != len(roots):
                raise ValueError(f"Expected {len(roots)} grad_outputs, got {len(provided)}")
            return provided

        seeds: list[Tensor] = []
        for index, root in enumerate(roots):
            if not root.is_scalar:
                raise ValueError(
                    f"backward() output {index} has shape {tuple(root.shape.dims)}; "
                    "pass grad_outputs explicitly or reduce it to a scalar first"
                )
            seeds.append(ones_like(root))
        return seeds


def _sum_tensors(tensors: Sequence[Tensor]) -> Tensor:
    """Sum a sequence of tensors that already share a shape."""
    total = tensors[0]
    for other in tensors[1:]:
        total = total + other
    return total


def _broadcast_like(grad: Tensor, target: Tensor) -> Tensor:
    """Return ``grad`` expanded to ``target``'s shape.

    Returns a read-only view when ``grad`` only needs broadcasting, and a real
    tensor when the result is written to, which the accumulation path does.
    """
    if grad.shape == target.shape:
        return grad
    if grad.numel == 1 or grad.ndim <= target.ndim:
        aligned = grad.shape.broadcast_to(target.shape)
        if aligned == grad.shape:
            return grad
        return Tensor.from_numpy(
            np.broadcast_to(grad.numpy(), tuple(target.shape.dims)).copy(),
            grad.dtype,
            grad.device,
        )
    if grad.numel == target.numel:
        return grad.reshape(target.shape)
    raise ValueError(
        f"Cannot align gradient of shape {tuple(grad.shape.dims)} to output "
        f"shape {tuple(target.shape.dims)}"
    )


def _align_to_output(output: Tensor, grad: Tensor) -> Tensor:
    """Reshape ``grad`` to ``output``'s shape when it holds the same elements."""
    if output.shape == grad.shape:
        return grad
    if output.numel == grad.numel:
        return grad.reshape(output.shape)
    raise ValueError(
        f"Gradient shape {tuple(grad.shape.dims)} is not compatible with output "
        f"shape {tuple(output.shape.dims)}"
    )


def _align_to_outputs(node: GraphNode, grad: Tensor) -> Tensor:
    """Align a caller-supplied seed to the node's primary output."""
    if not node.outputs or grad.shape == node.outputs[0].shape:
        return grad
    return _broadcast_like(grad, node.outputs[0])


def zeros_like(t: Tensor) -> Tensor:
    """Return a zero tensor shaped and typed like ``t``."""
    return Tensor.zeros(t.shape.dims, t.dtype, t.device)


def ones_like(t: Tensor) -> Tensor:
    """Return a one tensor shaped and typed like ``t``."""
    return Tensor.ones(t.shape.dims, t.dtype, t.device)


def full_like(t: Tensor, value: float) -> Tensor:
    """Return a tensor shaped and typed like ``t``, filled with ``value``."""
    return Tensor.full(t.shape.dims, value, t.dtype, t.device)


def grad_norm(tensors: Iterable[Tensor]) -> float:
    """Return the L2 norm across ``tensors``, accumulating in float64."""
    total = 0.0
    for t in tensors:
        if t is None:
            continue
        array = t.numpy().astype("float64", copy=False)
        total += float((array**2).sum())
    return total**0.5


def clip_grad_norm(tensors: Sequence[Tensor], max_norm: float) -> float:
    """Scale gradients in place so their total L2 norm is at most ``max_norm``.

    Returns the norm before clipping, which is what training loops log.
    """
    total = grad_norm(tensors)
    if max_norm <= 0 or total <= max_norm or total == 0.0:
        return total
    scale = max_norm / (total + 1e-6)
    for t in tensors:
        if t is not None and t._grad is not None:
            t._grad = t._grad * scale
    return total


#: Process-wide engine used by :func:`backward`.
_ENGINE = Engine()


def backward(
    outputs: Tensor | Sequence[Tensor],
    grad_outputs: Tensor | Sequence[Tensor] | None = None,
    retain_graph: bool = False,
) -> BackwardResult:
    """Differentiate ``outputs`` using the process-wide engine."""
    return _ENGINE.backward(outputs, grad_outputs, retain_graph)
