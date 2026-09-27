"""AI IR graph."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIIRNode:
    node_id: str
    op: str
    inputs: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)


class AIIRGraph:
    def __init__(self) -> None:
        self._nodes: Dict[str, AIIRNode] = {}
        self._edges: List[tuple] = []

    def add_node(self, node: AIIRNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, source: str, target: str) -> None:
        self._edges.append((source, target))


ai_ir_graph = AIIRGraph()
