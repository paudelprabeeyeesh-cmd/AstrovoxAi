"""Model swarm for distributed inference."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SwarmNode:
    node_id: str
    model_id: str
    endpoint: str
    load: float = 0.0
    status: str = "available"
    last_health_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ModelSwarm:
    def __init__(self) -> None:
        self._nodes: Dict[str, SwarmNode] = {}

    def register_node(self, node: SwarmNode) -> None:
        self._nodes[node.node_id] = node

    def route_request(self, model_id: str) -> Optional[SwarmNode]:
        candidates = [n for n in self._nodes.values() if n.model_id == model_id and n.status == "available"]
        if not candidates:
            return None
        return min(candidates, key=lambda n: n.load)

    def update_load(self, node_id: str, load: float) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.load = load
            node.last_health_check = datetime.now(timezone.utc)


model_swarm = ModelSwarm()
