
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .engine import PolicyEngine, policy_engine, Policy
from .rules import PolicyRules


class PolicyEvaluator:
    def __init__(self):
        self.engine = policy_engine

    def evaluate_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self.engine.evaluate(context)

    def check_access(self, user_id: str, resource_type: str, resource_id: str, action: str, user_is_member: bool = False, user_role: str = "user") -> Dict[str, Any]:
        context = {
            "action": f"access_{resource_type}",
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "access_action": action,
            "user_is_member": user_is_member,
            "user_role": user_role,
        }
        return self.evaluate_request(context)

    def check_data_access(self, user_id: str, data_type: str, data_age_days: int) -> Dict[str, Any]:
        context = {
            "action": "access_data",
            "user_id": user_id,
            "data_type": data_type,
            "data_age_days": data_age_days,
        }
        return self.evaluate_request(context)

    def check_usage_limits(self, user_id: str, daily_tokens: int, monthly_cost_usd: float) -> Dict[str, Any]:
        context = {
            "action": "check_usage",
            "user_id": user_id,
            "daily_tokens": daily_tokens,
            "monthly_cost_usd": monthly_cost_usd,
        }
        return self.evaluate_request(context)

    def evaluate_sso_policy(self, user_id: str, plan: str, sso_enabled: bool, mfa_enabled: bool, user_role: str) -> Dict[str, Any]:
        context = {
            "action": "sso_authentication",
            "user_id": user_id,
            "plan": plan,
            "sso_enabled": sso_enabled,
            "mfa_enabled": mfa_enabled,
            "user_role": user_role,
        }
        return self.evaluate_request(context)

    def register_custom_policy(self, policy_id: str, name: str, rules: List[Dict[str, Any]], effect: str = "allow") -> None:
        policy = Policy(policy_id=policy_id, name=name, rules=rules, effect=effect)
        self.engine.register_policy(policy)

    def get_active_policies(self) -> List[Dict[str, Any]]:
        return self.engine.list_policies()

    def bulk_evaluate(self, contexts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self.evaluate_request(ctx) for ctx in contexts]


policy_evaluator = PolicyEvaluator()
