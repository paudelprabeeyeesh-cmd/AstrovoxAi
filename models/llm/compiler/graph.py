from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, Iterable, List, Optional, Set, Tuple

NodeId = Hashable


@dataclass
class Node:
    id: NodeId
    op: str
    attrs: Dict[str, Any] = field(default_factory=dict)
    shape: Optional[Tuple[int, ...]] = None
    dtype: Optional[str] = None

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class Edge:
    source: NodeId
    target: NodeId
    src_slot: int = 0
    dst_slot: int = 0
    attrs: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        return hash((self.source, self.target, self.src_slot, self.dst_slot))


class ComputationGraph:
    def __init__(self) -> None:
        self.nodes: Dict[NodeId, Node] = {}
        self.edges: List[Edge] = []
        self._outgoing: Dict[NodeId, List[Edge]] = {}
        self._incoming: Dict[NodeId, List[Edge]] = {}
        self._outputs: List[NodeId] = []

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise KeyError("Both source and target nodes must exist before adding an edge.")
        self.edges.append(edge)
        self._outgoing[edge.source].append(edge)
        self._incoming[edge.target].append(edge)

    def predecessors(self, node_id: NodeId) -> List[NodeId]:
        return [edge.source for edge in self._incoming.get(node_id, [])]

    def successors(self, node_id: NodeId) -> List[NodeId]:
        return [edge.target for edge in self._outgoing.get(node_id, [])]

    def set_outputs(self, outputs: Iterable[NodeId]) -> None:
        self._outputs = list(outputs)

    def outputs(self) -> List[NodeId]:
        return list(self._outputs)

    def subgraph(self, node_ids: Iterable[NodeId]) -> Subgraph:
        ids = set(node_ids)
        sub = Subgraph()
        for nid in ids:
            if nid not in self.nodes:
                continue
            sub.nodes.add(nid)
            node = self.nodes[nid]
            sub.node_map[nid] = Node(id=node.id, op=node.op, attrs=dict(node.attrs), shape=node.shape, dtype=node.dtype)
        for edge in self.edges:
            if edge.source in ids and edge.target in ids:
                sub.edges.append(edge)
                sub.edge_set.add(edge)
        return sub

    def topological_order(self) -> List[NodeId]:
        visited: Set[NodeId] = set()
        temp: Set[NodeId] = set()
        order: List[NodeId] = []

        def visit(nid: NodeId) -> None:
            if nid in temp:
                raise ValueError("Cycle detected in computation graph.")
            if nid in visited:
                return
            temp.add(nid)
            for succ in self.successors(nid):
                visit(succ)
            temp.remove(nid)
            visited.add(nid)
            order.append(nid)

        roots = [nid for nid in self.nodes if not self._incoming[nid]]
        if not roots:
            raise ValueError("Graph has no root nodes.")
        for root in roots:
            visit(root)
        order.reverse()
        return order


@dataclass
class Subgraph:
    nodes: Set[NodeId] = field(default_factory=set)
    edges: List[Edge] = field(default_factory=list)
    node_map: Dict[NodeId, Node] = field(default_factory=dict)
    edge_set: Set[Edge] = field(default_factory=set)


def topo_sort(graph: ComputationGraph) -> List[NodeId]:
    return graph.topological_order()
