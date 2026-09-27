"""Autoscaling configuration."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AutoscalingPolicy:
    policy_id: str
    service: str
    min_instances: int
    max_instances: int
    target_cpu: float = 70.0
    target_memory: float = 80.0


class AutoscalingManager:
    def __init__(self) -> None:
        self._policies: Dict[str, AutoscalingPolicy] = {}

    def add_policy(self, policy: AutoscalingPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[AutoscalingPolicy]:
        return self._policies.get(policy_id)


autoscaling_manager = AutoscalingManager()
