"""Data retention management."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetentionPolicy:
    policy_id: str
    resource_type: str
    retention_days: int
    action: str


class RetentionManager:
    def __init__(self) -> None:
        self._policies: Dict[str, RetentionPolicy] = {}

    def add_policy(self, policy: RetentionPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def apply(self, resource_type: str, created_at: datetime) -> bool:
        policy = next((p for p in self._policies.values() if p.resource_type == resource_type), None)
        if not policy:
            return True
        age_days = (datetime.now(timezone.utc) - created_at).days
        return age_days < policy.retention_days


retention_manager = RetentionManager()
