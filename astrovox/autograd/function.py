"""Autograd function protocol and the dynamic computation graph.

A :class:`Function` records how one operation was applied to a set of
:class:`Node` inputs. The engine walks these records in reverse to produce
gradients, which keeps forward execution free of any derivative bookkeeping
beyond building the node.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

#: A node is any object that can carry a gradient. Tensors implement it, and
#: tests can supply lightweight stand-ins.
Node = Any


class Function:
    """Base class for a differentiable operation.

    Subclasses implement :meth:`forward` and :meth:`backward`. The engine calls
    :meth:`apply` to run the forward pass and attach a node to the graph.
    """

    #: Human-readable operation name, used by the compiler and profiler.
    name: str = "Function"

    @staticmethod
    def forward(ctx: Any, *args: Node) -> Node:
        """Compute the forward result. ``ctx`` is scratch state for backward."""
        raise NotImplementedError

    @staticmethod
    def backward(ctx: Any, grad_output: Node) -> tuple[Node | None, ...]:
        """Return one gradient per forward input, or ``None`` to skip.

        Returning ``None`` for an input marks that input as not requiring
        gradient, which lets the engine avoid computing it at all.
        """
        raise NotImplementedError

    @classmethod
    def apply(cls, *args: Node, **kwargs: Any) -> Node:
        """Run the forward pass and, if needed, record a graph node.

        Grad mode is honoured: under ``no_grad`` no node is created, so the
        result carries no graph and backward is a no-op.
        """
        from astrovox.autograd.graph import GraphContext, current_graph

        graph = current_graph()
        ctx = _FunctionContext()
        result = cls.forward(ctx, *args, **kwargs)
        if graph.is_enabled() and cls._requires_grad(args, result):
            outputs = tuple(result) if isinstance(result, tuple) else (result,)
            node = GraphNode(cls, ctx, tuple(args), outputs)
            for output in outputs:
                set_tensor_grad_fn(output, node)
        return result

    @staticmethod
    def _requires_grad(args: Sequence[Node], result: Node) -> bool:
        """Return whether any input requires grad, i.e. the node is needed.

        Duck-typed on purpose: a class annotation is not a runtime attribute,
        so ``isinstance`` against a bare protocol class would never match.
        """
        if isinstance(result, tuple):
            return any(bool(getattr(r, "requires_grad", False)) for r in result)
        return bool(getattr(result, "requires_grad", False))


class _TensorProtocol:
    """Structural type describing what the graph needs from a tensor."""

    requires_grad: bool
    _grad_fn: Any


def set_tensor_grad_fn(tensor: object, node: "GraphNode | None") -> None:
    """Attach or clear the graph node that produced ``tensor``."""
    try:
        tensor._grad_fn = node  # type: ignore[attr-defined]
    except AttributeError:
        pass


class _FunctionContext:
    """Per-invocation scratch space saved between forward and backward.

    Kernels stash intermediate values here (for example the softmax output
    needed to compute a Jacobian) so the forward pass does not recompute them.
    """

    __slots__ = ("saved", "needs_input_grad", "name")

    def __init__(self) -> None:
        self.saved: dict[str, Any] = {}
        self.needs_input_grad: list[bool] = []
        self.name: str | None = None

    def save(self, **kwargs: Any) -> None:
        """Store tensors or scalars needed during backward."""
        self.saved.update(kwargs)

    def load(self, key: str, default: Any = None) -> Any:
        """Retrieve a previously saved value."""
        return self.saved.get(key, default)

    def set_needs_input_grad(self, flags: Iterable[bool]) -> None:
        """Record which forward inputs require gradients."""
        self.needs_input_grad = list(flags)

    def mark_dirty(self, *tensors: Any) -> None:
        """Declare tensors mutated in place so the engine invalidates views."""

    def __repr__(self) -> str:
        return f"_FunctionContext(saved={sorted(self.saved)})"


class GraphNode:
    """One recorded operation in the dynamic computation graph."""

    __slots__ = ("function", "ctx", "inputs", "outputs", "name", "sequence_nr", "next_functions")

    def __init__(
        self,
        function: type[Function],
        ctx: _FunctionContext,
        inputs: tuple[Node, ...],
        outputs: tuple[Node, ...],
    ) -> None:
        self.function = function
        self.ctx = ctx
        self.inputs = inputs
        self.outputs = outputs
        self.name = function.name
        from astrovox.autograd.graph import GraphContext

        GraphContext.next_sequence_nr()
        self.sequence_nr = GraphContext.sequence_nr
        self.next_functions: list[tuple[GraphNode | None, int]] = []
        for tensor in inputs:
            grad_fn = getattr(tensor, "_grad_fn", None)
            self.next_functions.append((grad_fn, 0) if grad_fn is not None else (None, 0))

    @property
    def input_count(self) -> int:
        """Number of forward inputs this node received."""
        return len(self.inputs)

    def next_functions_for(self, index: int) -> tuple[GraphNode | None, int]:
        """Return the ``(node, output_index)`` pair for input ``index``."""
        return self.next_functions[index]

    def __repr__(self) -> str:
        inputs = ", ".join(str(getattr(t, "shape", "?")) for t in self.inputs)
        return f"<{self.name} #{self.sequence_nr}({inputs})>"


def sequence_counter() -> int:
    """Return the number of graph nodes created so far."""
    return GraphContext.sequence_nr
