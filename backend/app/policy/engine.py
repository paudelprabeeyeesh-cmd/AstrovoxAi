"""Policy engine for governance and access control."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Policy:
    policy_id: str
    name: str
    effect: str
    actions: List[str]
    resources: List[str]
    conditions: Optional[Callable[..., Any]] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyDecision:
    policy_id: str
    effect: str
    allowed: bool
    reason: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: List[Policy] = []

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)
        logger.info("Added policy %s: %s", policy.policy_id, policy.name)

    def remove_policy(self, policy_id: str) -> None:
        self._policies = [p for p in self._policies if p.policy_id != policy_id]

    def evaluate(self, action: str, resource: str, context: Optional[Dict[str, Any]] = None) -> PolicyDecision:
        context = context or {}
        for policy in self._policies:
            if action in policy.actions and resource in policy.resources:
                if policy.conditions:
                    try:
                        if not policy.conditions(context):
                            continue
                    except Exception:
                        logger.exception("Policy condition evaluation failed for %s", policy.policy_id)
                        continue
                allowed = policy.effect == "allow"
                return PolicyDecision(
                    policy_id=policy.policy_id,
                    effect=policy.effect,
                    allowed=allowed,
                    reason=f"Matched policy {policy.name}",
                )
        return PolicyDecision(
            policy_id="default",
            effect="deny",
            allowed=False,
            reason="No matching policy found",
        )

    def evaluate_batch(self, requests: List[Dict[str, Any]]) -> List[PolicyDecision]:
        return [self.evaluate(req["action"], req["resource"], req.get("context")) for req in requests]


policy_engine = PolicyEngine()
