"""Load balancer configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BalancerConfig:
    lb_id: str
    algorithm: str
    endpoints: List[str]
    health_check_path: str = "/health"
    sticky_sessions: bool = False


class LoadBalancer:
    def __init__(self) -> None:
        self._configs: Dict[str, BalancerConfig] = {}

    def create(self, config: BalancerConfig) -> BalancerConfig:
        self._configs[config.lb_id] = config
        return config

    def get_endpoint(self, lb_id: str) -> Optional[str]:
        config = self._configs.get(lb_id)
        if config and config.endpoints:
            return config.endpoints[0]
        return None


load_balancer = LoadBalancer()
