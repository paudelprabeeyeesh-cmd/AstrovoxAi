"""AI knowledge graph."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIGraphNode:
    node_id: str
    label: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AIGraphEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)


class AIKnowledgeGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, AIGraphNode] = {}
        self._edges: List[AIGraphEdge] = []

    def add_node(self, node: AIGraphNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, relation: str) -> AIGraphEdge:
        edge_id = uuid.uuid4().hex
        edge = AIGraphEdge(edge_id=edge_id, source_id=source_id, target_id=target_id, relation=relation)
        self._edges.append(edge)
        return edge


ai_knowledge_graph = AIKnowledgeGraph()
