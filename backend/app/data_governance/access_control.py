"""Access control for data governance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AccessPolicy:
    policy_id: str
    subject: str
    resource: str
    action: str
    effect: str


class DataAccessController:
    def __init__(self) -> None:
        self._policies: Dict[str, AccessPolicy] = {}

    def add_policy(self, policy: AccessPolicy) -> None:
        self._policies[policy.policy_id] = policy

    def check(self, subject: str, resource: str, action: str) -> bool:
        for policy in self._policies.values():
            if policy.subject == subject and policy.resource == resource and policy.action == action:
                return policy.effect == "allow"
        return False


data_access_controller = DataAccessController()
