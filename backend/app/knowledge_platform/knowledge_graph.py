"""Knowledge graph for structured knowledge representation."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    node_id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []

    def add_node(self, node: GraphNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, relation: str) -> GraphEdge:
        edge_id = uuid.uuid4().hex
        edge = GraphEdge(edge_id=edge_id, source_id=source_id, target_id=target_id, relation=relation)
        self._edges.append(edge)
        return edge

    def query(self, node_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        result = [{"node": self._nodes.get(node_id).__dict__ if node_id in self._nodes else None}]
        for edge in self._edges:
            if edge.source_id == node_id:
                target = self._nodes.get(edge.target_id)
                if target:
                    result.append({"node": target.__dict__, "relation": edge.relation})
        return result


knowledge_graph = KnowledgeGraph()
