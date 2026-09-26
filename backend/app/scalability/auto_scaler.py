"""Auto-scaling for compute resources."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScalingPolicy:
    policy_id: str
    service: str
    min_instances: int
    max_instances: int
    target_cpu: float = 70.0
    scale_up_cooldown_seconds: int = 60
    scale_down_cooldown_seconds: int = 300


class AutoScaler:
    def __init__(self) -> None:
        self._policies: Dict[str, ScalingPolicy] = {}
        self._instances: Dict[str, int] = {}

    def add_policy(self, policy: ScalingPolicy) -> None:
        self._policies[policy.policy_id] = policy
        self._instances[policy.service] = policy.min_instances

    def evaluate(self, service: str, cpu_utilization: float) -> Optional[Dict[str, Any]]:
        policy = next((p for p in self._policies.values() if p.service == service), None)
        if not policy:
            return None
        current = self._instances.get(service, policy.min_instances)
        if cpu_utilization > policy.target_cpu and current < policy.max_instances:
            self._instances[service] = current + 1
            return {"service": service, "action": "scale_up", "new_count": current + 1}
        if cpu_utilization < policy.target_cpu * 0.5 and current > policy.min_instances:
            self._instances[service] = current - 1
            return {"service": service, "action": "scale_down", "new_count": current - 1}
        return None


auto_scaler = AutoScaler()
