"""Dynamic computation graph construction.

The graph is implicit: tensors carry a pointer to the node that produced them,
and nodes point at their input nodes. Building it costs one pointer per
operation, and the engine traverses it without a separate topologically sorted
structure.
"""

from __future__ import annotations

import threading
from typing import Iterator

from astrovox.autograd.function import GraphNode, Node


class GraphContext:
    """Thread-local state controlling whether the graph is being recorded."""

    _local = threading.local()
    sequence_nr: int = 0

    @classmethod
    def _state(cls) -> "_State":
        state = getattr(cls._local, "state", None)
        if state is None:
            state = _State()
            cls._local.state = state
        return state

    @classmethod
    def next_sequence_nr(cls) -> int:
        """Advance and return the node sequence counter."""
        cls.sequence_nr += 1
        return cls.sequence_nr

    @classmethod
    def is_enabled(cls) -> bool:
        """Return whether new operations are being recorded."""
        return cls._state().enabled

    @classmethod
    def set_enabled(cls, value: bool) -> None:
        """Enable or disable graph recording."""
        cls._state().enabled = bool(value)

    @classmethod
    def retain_graph(cls) -> bool:
        """Return whether the graph is kept after backward."""
        return cls._state().retain_graph

    @classmethod
    def set_retain_graph(cls, value: bool) -> None:
        """Control whether the graph survives a backward pass."""
        cls._state().retain_graph = bool(value)


class _State:
    """Mutable holder for the per-thread graph flags."""

    __slots__ = ("enabled", "retain_graph")

    def __init__(self) -> None:
        self.enabled = True
        self.retain_graph = False


class no_grad:
    """Context manager that disables graph recording inside its block.

    Inference code runs under this so that no nodes are allocated and the
    produced tensors have no backward path.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._previous = True

    def __enter__(self) -> "no_grad":
        self._previous = GraphContext.is_enabled()
        GraphContext.set_enabled(not self.enabled)
        return self

    def __exit__(self, *exc_info: object) -> None:
        GraphContext.set_enabled(self._previous)


class enable_grad:
    """Context manager that forces graph recording inside its block."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._previous = True

    def __enter__(self) -> "enable_grad":
        self._previous = GraphContext.is_enabled()
        GraphContext.set_enabled(self.enabled)
        return self

    def __exit__(self, *exc_info: object) -> None:
        GraphContext.set_enabled(self._previous)


def current_graph() -> GraphContext:
    """Return the graph context for the calling thread."""
    return GraphContext


def is_grad_enabled() -> bool:
    """Return whether autograd recording is active."""
    return GraphContext.is_enabled()


def walk_from(tensors: list[Node]) -> Iterator[GraphNode]:
    """Yield every node reachable from ``tensors``, in reverse creation order.

    Nodes are visited at most once even when a node is consumed by several
    downstream operations, so shared subgraphs are not re-expanded.
    """
    seen: set[int] = set()
    stack: list[GraphNode] = []
    for tensor in tensors:
        grad_fn = getattr(tensor, "_grad_fn", None)
        if grad_fn is not None:
            stack.append(grad_fn)

    while stack:
        node = stack.pop()
        key = id(node)
        if key in seen:
            continue
        seen.add(key)
        yield node
        for parent, _ in node.next_functions:
            if parent is not None and id(parent) not in seen:
                stack.append(parent)


def graph_size(tensors: list[Node]) -> int:
    """Return the number of nodes reachable from ``tensors``."""
    return sum(1 for _ in walk_from(tensors))


def topological_order(tensors: list[Node]) -> list[GraphNode]:
    """Return reachable nodes ordered so every producer precedes consumers.

    The engine's reverse pass already visits nodes in a valid topological
    order; this helper exists for the compiler, which needs the forward order.
    """
    return list(reversed(list(walk_from(tensors))))


def free_graph(tensors: list[Node]) -> int:
    """Detach ``tensors`` from their graph and return nodes released.

    Call this after a backward pass when the graph was not retained, so
    intermediate buffers can be reclaimed before the next iteration.
    """
    released = 0
    for tensor in tensors:
        grad_fn = getattr(tensor, "_grad_fn", None)
        if grad_fn is not None:
            released += graph_size([tensor])
            set_tensor_grad_fn(tensor, None)
    return released


def set_tensor_grad_fn(tensor: object, node: GraphNode | None) -> None:
    """Attach or clear the graph node on ``tensor``."""
    try:
        tensor._grad_fn = node  # type: ignore[attr-defined]
    except AttributeError:
        pass
