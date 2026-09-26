"""Policy engine for governance."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Policy:
    policy_id: str
    name: str
    description: str
    effect: str
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyEvaluation:
    policy_id: str
    allowed: bool
    reason: str
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: Dict[str, Policy] = {}

    def add_policy(self, policy: Policy) -> None:
        self._policies[policy.policy_id] = policy

    def evaluate(self, context: Dict[str, Any]) -> PolicyEvaluation:
        for policy in self._policies.values():
            if self._matches(policy, context):
                return PolicyEvaluation(policy_id=policy.policy_id, allowed=policy.effect == "allow", reason=policy.name)
        return PolicyEvaluation(policy_id="default", allowed=True, reason="default")

    def _matches(self, policy: Policy, context: Dict[str, Any]) -> bool:
        return all(context.get(k) == v for k, v in policy.conditions.items())


policy_engine = PolicyEngine()
