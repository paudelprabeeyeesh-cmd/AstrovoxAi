"""AI load balancer."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AILoadBalancerConfig:
    nodes: List[str]
    strategy: str = "round_robin"


class AILoadBalancer:
    def __init__(self, config: AILoadBalancerConfig) -> None:
        self.config = config
        self._index = 0

    def get_node(self) -> Optional[str]:
        if not self.config.nodes:
            return None
        node = self.config.nodes[self._index % len(self.config.nodes)]
        self._index += 1
        return node


ai_load_balancer = AILoadBalancer(AILoadBalancerConfig(nodes=[]))
