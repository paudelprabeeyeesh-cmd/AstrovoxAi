"""Data lineage tracking for governance and compliance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LineageNode:
    node_id: str
    name: str
    node_type: str
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LineageEdge:
    source_id: str
    target_id: str
    transformation: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataLineageTracker:
    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []

    def register_node(self, node: LineageNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, transformation: str) -> None:
        self._edges.append(LineageEdge(source_id=source_id, target_id=target_id, transformation=transformation))

    def get_upstream(self, node_id: str) -> List[LineageNode]:
        return [self._nodes[e.source_id] for e in self._edges if e.target_id == node_id and e.source_id in self._nodes]

    def get_downstream(self, node_id: str) -> List[LineageNode]:
        return [self._nodes[e.target_id] for e in self._edges if e.source_id == node_id and e.target_id in self._nodes]

    def visualize(self, root_id: str) -> Dict[str, Any]:
        visited = set()

        def walk(node_id: str) -> Dict[str, Any]:
            if node_id in visited:
                return {}
            visited.add(node_id)
            node = self._nodes.get(node_id)
            if not node:
                return {}
            children = [walk(e.target_id) for e in self._edges if e.source_id == node_id]
            return {
                "node_id": node.node_id,
                "name": node.name,
                "type": node.node_type,
                "children": [c for c in children if c],
            }

        return walk(root_id)


data_lineage_tracker = DataLineageTracker()
