"""Graph RAG for retrieval over knowledge graphs."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    id: str
    name: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)


class GraphRAG:
    """Graph-based RAG using entity-relation graphs for retrieval and reasoning."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self._adjacency: Dict[str, List[GraphEdge]] = {}

    def add_node(self, node_id: str, name: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self.nodes[node_id] = GraphNode(id=node_id, name=name, node_type=node_type, properties=properties or {})
        self._adjacency.setdefault(node_id, [])

    def add_edge(self, source_id: str, target_id: str, relation: str, properties: Optional[Dict[str, Any]] = None) -> None:
        if source_id not in self.nodes or target_id not in self.nodes:
            return
        edge = GraphEdge(source_id=source_id, target_id=target_id, relation=relation, properties=properties or {})
        self.edges.append(edge)
        self._adjacency.setdefault(source_id, []).append(edge)
        self._adjacency.setdefault(target_id, []).append(edge)

    def retrieve(self, query: str, top_k: int = 5, traversal_depth: int = 2) -> List[Dict[str, Any]]:
        candidates = []
        query_terms = set(query.lower().split())
        for node_id, node in self.nodes.items():
            score = self._relevance(query_terms, node)
            candidates.append({"id": node_id, "name": node.name, "type": node.node_type, "score": score})
        candidates.sort(key=lambda x: x["score"], reverse=True)
        expanded = []
        seen = set()
        for cand in candidates[:top_k]:
            if cand["id"] in seen:
                continue
            seen.add(cand["id"])
            expanded.append(cand)
            neighbors = self._get_neighbors(cand["id"], traversal_depth)
            for nid in neighbors:
                if nid not in seen:
                    seen.add(nid)
                    n = self.nodes.get(nid)
                    if n:
                        expanded.append({"id": nid, "name": n.name, "type": n.node_type, "score": 0.0})
        return expanded[:top_k]

    def _relevance(self, query_terms: Set[str], node: GraphNode) -> float:
        name_terms = set(node.name.lower().split())
        overlap = len(query_terms & name_terms)
        return overlap / max(len(query_terms), 1)

    def _get_neighbors(self, node_id: str, depth: int) -> List[str]:
        visited = {node_id}
        frontier = [node_id]
        for _ in range(depth):
            next_frontier = []
            for nid in frontier:
                for edge in self._adjacency.get(nid, []):
                    neighbor = edge.target_id if edge.source_id == nid else edge.source_id
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier
        return frontier

    def get_subgraph(self, node_id: str, depth: int = 2) -> List[Dict[str, Any]]:
        if node_id not in self.nodes:
            return []
        nodes = {node_id}
        frontier = [node_id]
        for _ in range(depth):
            next_frontier = []
            for nid in frontier:
                for edge in self._adjacency.get(nid, []):
                    neighbor = edge.target_id if edge.source_id == nid else edge.source_id
                    if neighbor not in nodes:
                        nodes.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier
        result = []
        for nid in nodes:
            node = self.nodes.get(nid)
            if node:
                result.append({"id": nid, "name": node.name, "type": node.node_type})
        return result
