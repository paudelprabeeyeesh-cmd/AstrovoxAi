from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PolicyRule:
    name: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[str] = field(default_factory=list)
    effect: str = "deny"
    priority: int = 0


@dataclass
class Policy:
    id: str
    name: str
    rules: List[PolicyRule] = field(default_factory=list)
    effect: str = "deny"
    priority: int = 0


class PolicyEngine:
    def __init__(self) -> None:
        self._policies: List[Policy] = []

    def add_policy(self, policy: Policy) -> None:
        self._policies.append(policy)

    def evaluate(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        context = context or {}
        policies = sorted(self._policies, key=lambda p: p.priority, reverse=True)
        for policy in policies:
            matched = [r for r in policy.rules if self._match_rule(r, subject, resource, action, context)]
            if matched:
                return policy.effect
        return "deny"

    def allowed_actions(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        context = context or {}
        actions: set = set()
        for policy in self._policies:
            if policy.effect == "deny":
                continue
            for rule in policy.rules:
                if self._match_conditions(rule.conditions, subject, resource, "", context):
                    actions.update(rule.actions)
        return sorted(actions)

    def escalate(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        matched: List[Dict[str, Any]] = []
        for policy in self._policies:
            matched_rules = [r for r in policy.rules if self._match_rule(r, subject, resource, action, context or {})]
            if matched_rules:
                matched.append({"policy": policy.name, "rules": [r.name for r in matched_rules], "effect": policy.effect})
        return matched or None

    def _match_rule(
        self,
        rule: PolicyRule,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        if rule.actions and action not in rule.actions:
            return False
        return self._match_conditions(rule.conditions, subject, resource, action, context)

    def _match_conditions(
        self,
        conditions: Dict[str, Any],
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        context: Dict[str, Any],
    ) -> bool:
        for key, expected in conditions.items():
            if key == "action":
                if expected != action:
                    return False
            elif key == "subject.role":
                if subject.get("role") != expected:
                    return False
            elif key == "resource.type":
                if resource.get("type") != expected:
                    return False
            else:
                if context.get(key) != expected:
                    return False
        return True


class RBACEngine:
    def __init__(self) -> None:
        self._roles: Dict[str, List[str]] = {}

    def add_role(self, role: str, perms: List[str]) -> None:
        self._roles[role] = list(perms)

    def has_permission(self, role: str, perm: str) -> bool:
        return perm in self._roles.get(role, [])

    def roles_for(self, perms: List[str]) -> List[str]:
        return [role for role, p in self._roles.items() if all(perm in p for perm in perms)]

    def assign_permission(self, role: str, perm: str) -> None:
        self._roles.setdefault(role, []).append(perm)
