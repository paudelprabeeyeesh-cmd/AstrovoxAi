"""Graph optimization passes for the computation graph.

These are local, standalone utilities. Integration with the runtime graph
is expected to happen in a follow-up step so this module can be reviewed
independently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Node:
    name: str
    op: str
    inputs: tuple[str, ...] = ()
    attrs: dict = field(default_factory=dict)


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    outputs: tuple[str, ...] = ()

    def add(self, node: Node) -> None:
        self.nodes[node.name] = node

    def reachable(self) -> set[str]:
        visited: set[str] = set()
        stack = list(self.outputs)
        while stack:
            name = stack.pop()
            if name in visited:
                continue
            visited.add(name)
            node = self.nodes.get(name)
            if node:
                stack.extend(node.inputs)
        return visited


def dead_code_elimination(graph: Graph) -> Graph:
    reachable = graph.reachable()
    return Graph(
        nodes={name: node for name, node in graph.nodes.items() if name in reachable},
        outputs=tuple(name for name in graph.outputs if name in reachable),
    )


def _shape_rank(shape: Sequence[int] | None) -> int:
    return len(shape) if shape is not None else 0


def _is_broadcastable(left: Sequence[int], right: Sequence[int]) -> bool:
    for a, b in zip(reversed(left), reversed(right)):
        if a != 1 and b != 1 and a != b:
            return False
    return True


def constant_folding(graph: Graph) -> Graph:
    folded: dict[str, Node] = {}
    for name, node in graph.nodes.items():
        if _can_fold(node, graph):
            value = _fold(node, graph)
            folded[name] = Node(name=name, op="constant", attrs={"value": value})
            continue
        folded[name] = node
    return Graph(nodes=folded, outputs=graph.outputs)


def _can_fold(node: Node, graph: Graph) -> bool:
    return node.op in {"add", "mul", "sub", "div"} and all(
        "value" in graph.nodes[i].attrs for i in node.inputs
    )


def _fold(node: Node, graph: Graph) -> float:
    left = _node_value(node.inputs[0], graph)
    right = _node_value(node.inputs[1], graph)
    if node.op == "add":
        return left + right
    if node.op == "sub":
        return left - right
    if node.op == "mul":
        return left * right
    if node.op == "div":
        return left / right if right != 0 else float("inf")
    return float("nan")


def _node_value(name: str, graph: Graph) -> float:
    node = graph.nodes.get(name)
    if node is None:
        return float("nan")
    value = node.attrs.get("value")
    if isinstance(value, (int, float)):
        return float(value)
    return float("nan")


def operator_fusion(graph: Graph) -> Graph:
    fused: dict[str, Node] = {}
    for name, node in graph.nodes.items():
        if _should_fuse(node, graph):
            replacement = _fused_node(node, graph)
            fused[name] = replacement
            continue
        fused[name] = node
    return Graph(nodes=fused, outputs=graph.outputs)


def _should_fuse(node: Node, graph: Graph) -> bool:
    if node.op != "matmul":
        return False
    producers = [graph.nodes[i] for i in node.inputs if i in graph.nodes]
    return any(producer.op in {"add", "bias"} for producer in producers)


def _fused_node(node: Node, graph: Graph) -> Node:
    return Node(name=node.name, op="fused_matmul_bias", inputs=node.inputs, attrs=node.attrs)


def optimize(graph: Graph) -> Graph:
    current = graph
    for _ in range(4):
        current = dead_code_elimination(current)
        current = constant_folding(current)
        current = operator_fusion(current)
    return current


def infer_shapes(graph: Graph, input_shapes: Dict[str, tuple[int, ...]]) -> Dict[str, tuple[int, ...]]:
    shapes = dict(input_shapes)
    for name, node in graph.nodes.items():
        if name in shapes:
            continue
        if node.op == "constant":
            value = node.attrs.get("value")
            shapes[name] = () if isinstance(value, (int, float)) else (len(value),) if hasattr(value, "__len__") else ()
        elif node.op in {"add", "mul", "sub", "div"} and len(node.inputs) >= 2:
            left = shapes.get(node.inputs[0])
            right = shapes.get(node.inputs[1])
            shapes[name] = _broadcast_shape(left, right)
        elif node.op == "matmul" and len(node.inputs) >= 2:
            left = shapes.get(node.inputs[0], ())
            right = shapes.get(node.inputs[1], ())
            shapes[name] = left[:-1] + right[-1:]
        elif node.op == "reshape" and node.inputs:
            shapes[name] = tuple(node.attrs.get("shape", shapes.get(node.inputs[0], ())))
        elif node.op == "transpose" and node.inputs:
            axes = node.attrs.get("axes", ())
            base = shapes.get(node.inputs[0], ())
            if axes:
                shapes[name] = tuple(base[i] for i in axes)
            else:
                shapes[name] = base[::-1]
        elif node.op == "fused_matmul_bias" and node.inputs:
            left = shapes.get(node.inputs[0], ())
            right = shapes.get(node.inputs[1], ())
            shapes[name] = left[:-1] + right[-1:]
    return shapes


def _broadcast_shape(left: tuple[int, ...] | None, right: tuple[int, ...] | None) -> tuple[int, ...]:
    if not left and not right:
        return ()
    if not left:
        return right
    if not right:
        return left
    result = []
    for a, b in zip(reversed(left), reversed(right)):
        result.append(a if b == 1 else b)
    while len(result) < max(len(left), len(right)):
        result.append(left[len(left) - len(result) - 1] if len(left) > len(result) else right[len(right) - len(result) - 1])
    return tuple(reversed(result))


def plan_memory(graph: Graph, shapes: Dict[str, tuple[int, ...]]) -> Dict[str, int]:
    allocation: Dict[str, int] = {}
    for name, shape in shapes.items():
        size = 1
        for dim in shape:
            size *= max(1, int(dim))
        allocation[name] = size * 4
    return allocation


def auto_kernel(graph: Graph, backend: str = "cpu") -> Graph:
    if backend != "cpu":
        return graph
    annotated = dict(graph.nodes)
    for name, node in annotated.items():
        if node.op == "matmul":
            annotated[name] = Node(name=name, op="matmul_cpu", inputs=node.inputs, attrs=node.attrs)
        elif node.op in {"add", "mul", "sub", "div"}:
            annotated[name] = Node(name=name, op=f"{node.op}_cpu", inputs=node.inputs, attrs=node.attrs)
    return Graph(nodes=annotated, outputs=graph.outputs)
