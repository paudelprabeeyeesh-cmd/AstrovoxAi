"""Tool permissions with RBAC."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PermissionLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class PermissionRule:
    tool_name: str
    roles: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    level: PermissionLevel = PermissionLevel.READ
    allow: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)


class ToolPermissions:
    """Role-based access control for tools."""

    def __init__(self):
        self._rules: Dict[str, List[PermissionRule]] = {}
        self._role_hierarchy: Dict[str, PermissionLevel] = {
            "user": PermissionLevel.READ,
            "editor": PermissionLevel.WRITE,
            "admin": PermissionLevel.ADMIN,
            "owner": PermissionLevel.OWNER,
        }

    def add_rule(self, rule: PermissionRule) -> None:
        self._rules.setdefault(rule.tool_name, []).append(rule)

    def remove_rule(self, tool_name: str, index: int = 0) -> bool:
        rules = self._rules.get(tool_name)
        if not rules:
            return False
        rules.pop(index)
        if not rules:
            del self._rules[tool_name]
        return True

    def check(
        self,
        tool_name: str,
        user_id: Optional[str] = None,
        roles: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        roles = roles or []
        context = context or {}
        rules = self._rules.get(tool_name, [])
        if not rules:
            return True
        matched = []
        for rule in rules:
            if not rule.allow:
                if self._rule_matches(rule, user_id, roles, context):
                    matched.append(rule)
                    continue
            if self._rule_matches(rule, user_id, roles, context):
                matched.append(rule)
        if not matched:
            return False
        allowed = [r for r in matched if r.allow]
        denied = [r for r in matched if not r.allow]
        if denied and not allowed:
            return False
        if allowed and denied:
            allowed_levels = [self._role_hierarchy.get(r, PermissionLevel.READ) for r in roles]
            max_allowed = max(allowed_levels, key=lambda x: list(PermissionLevel).index(x))
            for rule in denied:
                if self._role_hierarchy.get(rule.level, PermissionLevel.READ) <= max_allowed:
                    return False
        return bool(allowed)

    def _rule_matches(
        self,
        rule: PermissionRule,
        user_id: Optional[str],
        roles: List[str],
        context: Dict[str, Any],
    ) -> bool:
        if rule.users and user_id not in rule.users:
            return False
        if rule.roles and not any(role in roles for role in rule.roles):
            return False
        for key, expected in rule.conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False
        return True

    def get_allowed_tools(self, user_id: Optional[str], roles: Optional[List[str]]) -> List[str]:
        roles = roles or []
        allowed: List[str] = []
        for tool_name, rules in self._rules.items():
            if self.check(tool_name, user_id, roles):
                allowed.append(tool_name)
        return allowed
