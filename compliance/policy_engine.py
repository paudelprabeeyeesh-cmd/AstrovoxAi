"""Policy engine for data retention, access control, and PII handling."""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Policy:
    id: str
    name: str
    description: str
    resource_type: str
    action: str
    condition: Callable[[dict], bool]
    effect: str = "deny"


class PolicyEngine:
    def __init__(self):
        self._policies: list[Policy] = []
        self._register_defaults()

    def _register_defaults(self):
        self.add_policy(Policy(
            id="p1",
            name="block_pii_export",
            description="Block exports containing PII",
            resource_type="export",
            action="read",
            condition=lambda ctx: "pii" in ctx.get("tags", []),
            effect="deny",
        ))
        self.add_policy(Policy(
            id="p2",
            name="retain_audit_logs_7y",
            description="Retain audit logs for 7 years",
            resource_type="compliance_log",
            action="delete",
            condition=lambda ctx: True,
            effect="deny",
        ))

    def add_policy(self, policy: Policy):
        self._policies.append(policy)

    def evaluate_action(self, actor_id: str, action: str, resource_type: str, context: dict) -> dict:
        matches = []
        for policy in self._policies:
            if policy.resource_type == resource_type and policy.action == action:
                try:
                    if policy.condition(context):
                        matches.append(policy)
                except Exception as exc:
                    logger.error("Policy %s evaluation failed: %s", policy.id, exc)
        if not matches:
            return {"allowed": True, "matched_policies": []}
        deny = any(p.effect == "deny" for p in matches)
        return {
            "allowed": not deny,
            "matched_policies": [p.id for p in matches],
            "effect": "deny" if deny else "allow",
        }

    def list_policies(self) -> list[dict]:
        return [{"id": p.id, "name": p.name, "resource_type": p.resource_type, "action": p.action, "effect": p.effect} for p in self._policies]


policy_engine = PolicyEngine()
