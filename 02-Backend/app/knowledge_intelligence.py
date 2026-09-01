"""Knowledge Intelligence — knowledge graph, automatic tagging, entity extraction."""

import time
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    name: str
    node_type: str
    properties: dict = field(default_factory=dict)
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph."""
    id: str
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0


class KnowledgeGraph:
    """Knowledge graph for organizing information."""

    def __init__(self):
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[KnowledgeEdge] = []

    def add_node(self, name: str, node_type: str, properties: dict = None) -> KnowledgeNode:
        """Add a node."""
        import secrets
        node = KnowledgeNode(
            id=secrets.token_hex(8),
            name=name,
            node_type=node_type,
            properties=properties or {},
        )
        self._nodes[node.id] = node
        return node

    def add_edge(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0):
        """Add an edge."""
        import secrets
        edge = KnowledgeEdge(
            id=secrets.token_hex(8),
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
        )
        self._edges.append(edge)

    def get_related(self, node_id: str) -> list:
        """Get related nodes."""
        related = []
        for edge in self._edges:
            if edge.source_id == node_id:
                related.append(self._nodes.get(edge.target_id))
            elif edge.target_id == node_id:
                related.append(self._nodes.get(edge.source_id))
        return [r for r in related if r is not None]

    def search(self, query: str) -> list:
        query_lower = query.lower()
        return [
            n for n in self._nodes.values()
            if query_lower in n.name.lower()
        ]


knowledge_graph = KnowledgeGraph()
