"""Attribute-Based Access Control (ABAC)."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Effect(Enum):
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class ABACRule:
    rule_id: str
    effect: Effect
    resource_type: str
    actions: List[str]
    conditions: Dict[str, Any]
    description: str = ""
    priority: int = 100
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PolicyContext:
    subject: Dict[str, Any]
    resource: Dict[str, Any]
    action: str
    environment: Dict[str, Any] = field(default_factory=dict)


class ABACEngine:
    _rules: List[ABACRule] = []

    @classmethod
    def add_rule(cls, rule: ABACRule) -> None:
        cls._rules.append(rule)
        cls._rules.sort(key=lambda r: r.priority)

    @classmethod
    def evaluate(cls, context: PolicyContext) -> Effect:
        for rule in cls._rules:
            if cls._matches(rule, context):
                return rule.effect
        return Effect.DENY

    @classmethod
    def _matches(cls, rule: ABACRule, context: PolicyContext) -> bool:
        if rule.resource_type != context.resource.get("type"):
            return False
        if context.action not in rule.actions:
            return False
        for key, expected in rule.conditions.items():
            actual = context.subject.get(key) or context.environment.get(key) or context.resource.get(key)
            if actual != expected:
                return False
        return True

    @classmethod
    def is_allowed(cls, subject: Dict[str, Any], resource: Dict[str, Any], action: str, environment: Optional[Dict[str, Any]] = None) -> bool:
        context = PolicyContext(
            subject=subject,
            resource=resource,
            action=action,
            environment=environment or {},
        )
        return cls.evaluate(context) == Effect.ALLOW
