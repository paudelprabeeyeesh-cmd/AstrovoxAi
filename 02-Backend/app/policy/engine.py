
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .database import get_db


class Policy:
    def __init__(self, policy_id: str, name: str, rules: List[Dict[str, Any]], effect: str = "allow"):
        self.policy_id = policy_id
        self.name = name
        self.rules = rules
        self.effect = effect
        self.created_at = datetime.now(timezone.utc).isoformat()


class PolicyEngine:
    def __init__(self):
        self._policies: Dict[str, Policy] = {}

    def register_policy(self, policy: Policy) -> None:
        self._policies[policy.policy_id] = policy

    def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        for policy in self._policies.values():
            result = self._evaluate_policy(policy, context)
            if result["decision"] == "deny":
                return result
        return {"decision": "allow", "matched_policies": [p.policy_id for p in self._policies.values()]}

    def _evaluate_policy(self, policy: Policy, context: Dict[str, Any]) -> Dict[str, Any]:
        for rule in policy.rules:
            if self._match_rule(rule, context):
                return {
                    "decision": policy.effect,
                    "policy_id": policy.policy_id,
                    "policy_name": policy.name,
                    "matched_rule": rule,
                }
        return {"decision": "allow"}

    def _match_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        conditions = rule.get("conditions", {})
        for key, expected in conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    def list_policies(self) -> List[Dict[str, Any]]:
        return [
            {
                "policy_id": p.policy_id,
                "name": p.name,
                "effect": p.effect,
                "rules_count": len(p.rules),
            }
            for p in self._policies.values()
        ]


policy_engine = PolicyEngine()

policy_engine.register_policy(Policy(
    policy_id="access_control_org",
    name="Organization Access Control",
    effect="deny",
    rules=[
        {
            "conditions": {"action": "access_organization", "user_is_member": False},
        }
    ],
))

policy_engine.register_policy(Policy(
    policy_id="data_retention",
    name="Data Retention Policy",
    effect="deny",
    rules=[
        {
            "conditions": {"action": "access_old_data", "data_age_days": ">365"},
        }
    ],
))

policy_engine.register_policy(Policy(
    policy_id="usage_limits",
    name="Usage Limits Policy",
    effect="deny",
    rules=[
        {
            "conditions": {"action": "exceed_usage", "daily_tokens": ">1000000"},
        }
    ],
))
