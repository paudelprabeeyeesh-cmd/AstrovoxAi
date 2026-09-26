"""Intermediate representation for AI compiler."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class IRNode:
    node_id: str
    op: str
    inputs: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


class IRGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, IRNode] = {}
        self._edges: List[tuple] = []

    def add_node(self, node: IRNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, source: str, target: str) -> None:
        self._edges.append((source, target))

    def topological_sort(self) -> List[str]:
        in_degree = {node_id: 0 for node_id in self._nodes}
        adj = {node_id: [] for node_id in self._nodes}
        for source, target in self._edges:
            adj[source].append(target)
            in_degree[target] += 1
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order


ir_graph = IRGraph()
