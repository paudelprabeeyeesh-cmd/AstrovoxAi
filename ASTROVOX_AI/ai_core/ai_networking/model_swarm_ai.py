"""AI model swarm."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AISwarmNode:
    node_id: str
    model_id: str
    endpoint: str
    load: float = 0.0
    status: str = "available"


class AIModelSwarm:
    def __init__(self) -> None:
        self._nodes: Dict[str, AISwarmNode] = {}

    def register_node(self, node: AISwarmNode) -> None:
        self._nodes[node.node_id] = node

    def route(self, model_id: str) -> Optional[AISwarmNode]:
        candidates = [n for n in self._nodes.values() if n.model_id == model_id and n.status == "available"]
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.load)


ai_model_swarm = AIModelSwarm()
