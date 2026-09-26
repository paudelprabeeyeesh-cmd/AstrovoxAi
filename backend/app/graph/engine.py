"""Graph query engine for knowledge graph traversal."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    node_id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str
    properties: Dict[str, Any] = field(default_factory=dict)


class GraphQueryEngine:
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[GraphEdge]] = {}

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.node_id] = node
        self._adjacency.setdefault(node.node_id, [])

    def add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)
        self._adjacency.setdefault(edge.source_id, []).append(edge)

    def neighbors(self, node_id: str) -> List[GraphNode]:
        edges = self._adjacency.get(node_id, [])
        return [self._nodes[e.target_id] for e in edges if e.target_id in self._nodes]

    def bfs(self, start_id: str, max_depth: int = 3) -> List[GraphNode]:
        visited: Set[str] = set()
        queue = [(start_id, 0)]
        result = []
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)
            node = self._nodes.get(node_id)
            if node:
                result.append(node)
            for edge in self._adjacency.get(node_id, []):
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))
        return result

    def shortest_path(self, start_id: str, end_id: str, max_depth: int = 5) -> Optional[List[GraphNode]]:
        from collections import deque
        queue = deque([(start_id, [start_id])])
        visited = {start_id}
        while queue:
            node_id, path = queue.popleft()
            if node_id == end_id:
                return [self._nodes[nid] for nid in path]
            if len(path) > max_depth:
                continue
            for edge in self._adjacency.get(node_id, []):
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, path + [edge.target_id]))
        return None

    def query(self, start_id: str, relationship: Optional[str] = None, max_depth: int = 2) -> List[Dict[str, Any]]:
        results = []
        queue = [(start_id, 0)]
        visited = {start_id}
        while queue:
            node_id, depth = queue.pop(0)
            if depth > max_depth:
                continue
            for edge in self._adjacency.get(node_id, []):
                if relationship and edge.relationship != relationship:
                    continue
                if edge.target_id not in visited:
                    visited.add(edge.target_id)
                    node = self._nodes.get(edge.target_id)
                    if node:
                        results.append({"node": node, "edge": edge, "depth": depth + 1})
                    queue.append((edge.target_id, depth + 1))
        return results


graph_query_engine = GraphQueryEngine()
