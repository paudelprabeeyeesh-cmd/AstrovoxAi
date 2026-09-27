"""AI auto scaler."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing: Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIScalingPolicy:
    policy_id: str
    service: str
    min_instances: int
    max_instances: int
    target_cpu: float = 70.0


class AIAutoScaler:
    def __init__(self) -> None:
        self._policies: Dict[str, AIScalingPolicy] = {}
        self._instances: Dict[str, int] = {}

    def add_policy(self, policy: AIScalingPolicy) -> None:
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
        return None


ai_auto_scaler = AIAutoScaler()
