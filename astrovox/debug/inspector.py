"""Autograd debugger: inspect a graph, then check it is wired correctly.

The engine's failures were subtle precisely because a truncated graph still
runs and still lowers a loss. These tools make the wiring visible: which nodes
exist, what feeds them, in what order the backward pass visits them, and which
parameters ended up with no gradient at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

import numpy as np

from astrovox.autograd.function import GraphNode
from astrovox.autograd.graph import walk_from
from astrovox.tensor.tensor import Tensor


@dataclass
class NodeInfo:
    """A readable description of one graph node."""

    id: int
    sequence_nr: int
    op: str
    input_shapes: list[str]
    output_shapes: list[str]
    requires_grad: bool
    parents: list[str]
    saved_tensors: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return the node as a plain dictionary."""
        return {
            "id": self.id,
            "sequence_nr": self.sequence_nr,
            "op": self.op,
            "input_shapes": self.input_shapes,
            "output_shapes": self.output_shapes,
            "requires_grad": self.requires_grad,
            "parents": self.parents,
            "saved_tensors": self.saved_tensors,
        }


@dataclass
class GraphReport:
    """Everything known about one captured graph."""

    nodes: list[NodeInfo] = field(default_factory=list)
    roots: int = 0
    leaves: int = 0
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self.nodes)

    def ops(self) -> dict[str, int]:
        """Return a histogram of operation names."""
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.op] = counts.get(node.op, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))

    def execution_order(self) -> list[str]:
        """Return the operations in backward-pass order.

        The engine walks nodes by descending creation number, so this is the
        order a backward pass will actually use.
        """
        return [node.op for node in sorted(self.nodes, key=lambda n: n.sequence_nr, reverse=True)]

    def dead_parameters(self) -> list[str]:
        """Return the parameters that received no gradient.

        A parameter missing from a graph, or one whose gradient is exactly
        zero, will not be updated. Both are worth seeing explicitly.
        """
        dead = []
        for name, info in self.parameters.items():
            if not info["in_graph"]:
                dead.append(name)
            elif info["grad_is_zero"]:
                dead.append(name)
        return dead

    def non_finite_parameters(self) -> list[str]:
        """Return parameters whose gradient contains NaN or infinity."""
        return [
            name
            for name, info in self.parameters.items()
            if info.get("has_non_finite_grad")
        ]

    def to_dict(self) -> dict[str, Any]:
        """Return the whole report as a plain dictionary."""
        return {
            "node_count": self.node_count,
            "roots": self.roots,
            "leaves": self.leaves,
            "ops": self.ops(),
            "execution_order": self.execution_order(),
            "nodes": [n.to_dict() for n in self.nodes],
            "parameters": self.parameters,
            "dead_parameters": self.dead_parameters(),
            "non_finite_parameters": self.non_finite_parameters(),
        }

    def to_json(self, indent: int = 2) -> str:
        """Return the report as JSON."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_text(self, limit: int = 40) -> str:
        """Return a compact human-readable summary."""
        lines = [
            f"graph: {self.node_count} nodes, {self.leaves} leaves, {self.roots} root(s)",
            f"ops: {self.ops()}",
            "backward order: " + " -> ".join(self.execution_order()[:limit]),
        ]
        dead = self.dead_parameters()
        if dead:
            lines.append(f"DEAD PARAMETERS ({len(dead)}): " + ", ".join(dead[:20]))
        bad = self.non_finite_parameters()
        if bad:
            lines.append(f"NON-FINITE GRADIENTS ({len(bad)}): " + ", ".join(bad[:20]))
        return "\n".join(lines)

    def to_dot(self) -> str:
        """Return the graph in Graphviz DOT format.

        Edges point from producer to consumer, so rendering this shows the
        dataflow directly.
        """
        by_id = {n.id: n for n in self.nodes}
        lines = ["digraph autograd {", "  rankdir=LR;", '  node [shape=box, fontname="monospace"];']
        for node in self.nodes:
            label = f"{node.op}\\n{node.sequence_nr}"
            lines.append(f'  n{node.id} [label="{label}"];')
        for node in self.nodes:
            for parent in node.parents:
                parent_id = int(parent.split(":")[1]) if ":" in parent else None
                if parent_id is not None and parent_id in by_id:
                    lines.append(f"  n{parent_id} -> n{node.id};")
        lines.append("}")
        return "\n".join(lines)


def _shape_of(value: Any) -> str:
    """Return a short shape description for any graph operand."""
    shape = getattr(value, "shape", None)
    if shape is None:
        if isinstance(value, (int, float)):
            return f"scalar({value})"
        return type(value).__name__
    dims = tuple(shape.dims) if hasattr(shape, "dims") else tuple(shape)
    return str(dims)


def _saved_bytes(ctx: Any) -> dict[str, int]:
    """Return the byte size of each tensor a node saved for backward."""
    out: dict[str, int] = {}
    for key, value in getattr(ctx, "saved", {}).items():
        if isinstance(value, Tensor):
            out[key] = int(value.nbytes)
    return out


def inspect(
    outputs: Tensor | Sequence[Tensor],
    module: Any = None,
    include_parameters: bool = True,
) -> GraphReport:
    """Build a :class:`GraphReport` for the graph reaching ``outputs``.

    Call this *before* ``backward``. A backward pass releases the graph unless
    it was called with ``retain_graph=True``, so afterwards the report is empty
    by design rather than because nothing was recorded.

    Args:
        outputs: tensors whose graphs should be inspected.
        module: optional module whose parameters are checked for dead
            gradients, which is the usual reason to call this.
        include_parameters: whether to walk ``module``'s parameters.
    """
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    report = GraphReport(roots=len(roots))

    nodes = list(walk_from(roots))
    leaves: dict[int, Tensor] = {}
    storages: set[int] = set()
    for node in nodes:
        parents = [f"{p.name}:{id(p)}" for p, _ in node.next_functions if p is not None]
        report.nodes.append(
            NodeInfo(
                id=id(node),
                sequence_nr=node.sequence_nr,
                op=node.name,
                input_shapes=[_shape_of(i) for i in node.inputs],
                output_shapes=[_shape_of(o) for o in node.outputs],
                requires_grad=any(bool(getattr(i, "requires_grad", False)) for i in node.inputs),
                parents=parents,
                saved_tensors=_saved_bytes(node.ctx),
            )
        )
        for value in node.inputs:
            if isinstance(value, Tensor) and value.requires_grad:
                leaves[id(value)] = value
                storages.add(id(value._storage))
    for root in roots:
        if isinstance(root, Tensor) and root.requires_grad:
            leaves[id(root)] = root
    report.leaves = len(leaves)

    if module is not None and include_parameters:
        for name, param in module.named_parameters():
            grad = param.grad
            # A parameter usually reaches the graph through a view, for
            # example a transpose of a weight. Storage identity is what
            # matters, so a transposed weight still counts as connected.
            in_graph = id(param) in leaves or id(param._storage) in storages
            report.parameters[name] = {
                "shape": str(tuple(param.shape.dims)),
                "numel": param.numel,
                "in_graph": in_graph or param._grad_fn is not None,
                "grad_is_zero": grad is not None and not bool(np.any(grad.numpy() != 0.0)),
                "has_grad": grad is not None,
                "grad_norm": 0.0 if grad is None else float((grad.numpy() ** 2).sum() ** 0.5),
                "has_non_finite_grad": grad is not None and not bool(np.isfinite(grad.numpy()).all()),
            }
    return report


def check_graph(outputs: Tensor | Sequence[Tensor], module: Any = None) -> list[str]:
    """Return a list of problems found in the graph.

    Each entry names something that would silently produce a model that looks
    like it trains while part of it does not. Call this before ``backward``:
    the graph is released afterwards unless it was retained.
    """
    report = inspect(outputs, module)
    problems: list[str] = []

    # Graph reachability is only meaningful while the graph is still alive; a
    # backward pass releases it, and reporting everything as disconnected then
    # would be worse than saying nothing.
    if report.node_count > 0:
        disconnected = [name for name, info in report.parameters.items() if not info["in_graph"]]
        if disconnected:
            problems.append(
                f"{len(disconnected)} parameter(s) are not connected to the graph: "
                + ", ".join(disconnected)
            )

    after_backward = any(info["has_grad"] for info in report.parameters.values())
    if after_backward:
        dead = [name for name, info in report.parameters.items() if not info["has_grad"]]
        if dead:
            problems.append(
                f"{len(dead)} parameter(s) received no gradient and will not update: "
                + ", ".join(dead)
            )
        non_finite = report.non_finite_parameters()
        if non_finite:
            problems.append(
                f"{len(non_finite)} parameter(s) have a non-finite gradient: "
                + ", ".join(non_finite)
            )
    return problems


def gradient_table(module: Any) -> list[tuple[str, float, bool, bool]]:
    """Return ``(name, norm, is_zero, is_non_finite)`` per parameter."""
    rows = []
    for name, param in module.named_parameters():
        grad = param.grad
        if grad is None:
            rows.append((name, float("nan"), True, False))
            continue
        values = grad.numpy()
        rows.append(
            (
                name,
                float((values.astype("float64") ** 2).sum() ** 0.5),
                not bool(np.any(values != 0.0)),
                not bool(np.isfinite(values).all()),
            )
        )
    return rows


def format_gradient_table(module: Any) -> str:
    """Return the gradient table as aligned text."""
    header = f"{'parameter':<44}{'grad norm':>14}  status"
    lines = [header, "-" * len(header)]
    for name, norm, is_zero, is_non_finite in gradient_table(module):
        if is_non_finite:
            status = "NON-FINITE"
        elif is_zero:
            status = "ZERO"
        else:
            status = "ok"
        lines.append(f"{name:<44}{norm:>14.6g}  {status}")
    return "\n".join(lines)


def describe_tensor(t: Tensor) -> str:
    """Return a one-line description of a tensor, useful in log messages."""
    parts = [
        f"shape={tuple(t.shape.dims)}",
        f"dtype={t.dtype.name}",
        f"numel={t.numel}",
    ]
    if t.is_contiguous:
        parts.append("contiguous")
    else:
        parts.append(f"strided{t.stride}")
    if t.requires_grad:
        parts.append("requires_grad")
    if t._grad_fn is not None:
        parts.append(f"grad_fn={t._grad_fn.name}")
    return "Tensor(" + ", ".join(parts) + ")"


def find_constant_subgraphs(outputs: Tensor | Sequence[Tensor]) -> list[GraphNode]:
    """Return subgraphs whose inputs are all constants.

    Such a branch contributes a constant and is a candidate for folding away
    by the compiler.
    """
    roots = [outputs] if isinstance(outputs, Tensor) else list(outputs)
    return [
        node
        for node in walk_from(roots)
        if all(not bool(getattr(i, "requires_grad", False)) for i in node.inputs)
    ]
