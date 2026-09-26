"""Attribute-Based Access Control (ABAC) engine."""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .models import ORG_ROLES, WORKSPACE_ROLES
from .service import org_service

logger = logging.getLogger(__name__)


@dataclass
class ABACAttribute:
    key: str
    value: Any
    source: str = "static"


@dataclass
class ABACContext:
    user_id: str
    organization_id: str = ""
    workspace_id: str = ""
    attributes: List[ABACAttribute] = field(default_factory=list)
    resource_type: str = ""
    resource_id: str = ""
    action: str = ""
    environment: Dict[str, Any] = field(default_factory=dict)


class ABACEnforcer:
    """Attribute-Based Access Control with RBAC fallback."""

    def __init__(self):
        self._policies: List[Dict[str, Any]] = []
        self._default_deny = True

    def add_policy(self, policy: Dict[str, Any]) -> None:
        self._policies.append(policy)

    def evaluate(self, context: ABACContext) -> bool:
        for policy in self._policies:
            if self._matches(policy, context):
                effect = policy.get("effect", "deny")
                logger.debug("ABAC policy matched: effect=%s policy=%s", effect, policy.get("name"))
                return effect == "allow"
        return not self._default_deny

    def _matches(self, policy: Dict[str, Any], context: ABACContext) -> bool:
        conditions = policy.get("conditions", {})
        for attr, expected in conditions.items():
            actual = self._resolve_attribute(attr, context)
            if callable(expected):
                if not expected(actual):
                    return False
            elif actual != expected:
                return False
        return True

    def _resolve_attribute(self, attr: str, context: ABACContext) -> Any:
        if attr.startswith("user."):
            key = attr[5:]
            for a in context.attributes:
                if a.key == key and a.source == "user":
                    return a.value
            return None
        if attr.startswith("resource."):
            key = attr[9:]
            return context.environment.get(key)
        if attr == "organization_id":
            return context.organization_id
        if attr == "workspace_id":
            return context.workspace_id
        if attr == "action":
            return context.action
        if attr == "resource_type":
            return context.resource_type
        return None

    def has_org_permission(self, user_id: str, organization_id: str, permission: str) -> bool:
        membership = org_service.get_membership(organization_id, user_id)
        if not membership or membership.status not in ("active", "invited"):
            return False
        role_perms = ORG_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    def has_workspace_permission(self, user_id: str, workspace_id: str, permission: str) -> bool:
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        if not membership or membership.status not in ("active", "invited"):
            return False
        role_perms = WORKSPACE_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    def get_org_role(self, user_id: str, organization_id: str) -> Optional[str]:
        membership = org_service.get_membership(organization_id, user_id)
        return membership.role if membership and membership.status == "active" else None

    def get_workspace_role(self, user_id: str, workspace_id: str) -> Optional[str]:
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        return membership.role if membership and membership.status == "active" else None

    def can_manage_member(self, manager_id: str, target_id: str, organization_id: str) -> bool:
        manager_membership = org_service.get_membership(organization_id, manager_id)
        target_membership = org_service.get_membership(organization_id, target_id)
        if not manager_membership or not target_membership:
            return False
        role_hierarchy = ["guest", "member", "manager", "admin", "owner"]
        manager_level = role_hierarchy.index(manager_membership.role) if manager_membership.role in role_hierarchy else 0
        target_level = role_hierarchy.index(target_membership.role) if target_membership.role in role_hierarchy else 0
        return manager_level > target_level

    def require_org_role(self, user_id: str, organization_id: str, min_role: str) -> bool:
        membership = org_service.get_membership(organization_id, user_id)
        if not membership or membership.status not in ("active", "invited"):
            return False
        role_hierarchy = ["guest", "member", "manager", "admin", "owner"]
        user_level = role_hierarchy.index(membership.role) if membership.role in role_hierarchy else 0
        required_level = role_hierarchy.index(min_role) if min_role in role_hierarchy else 0
        return user_level >= required_level

    def require_workspace_role(self, user_id: str, workspace_id: str, min_role: str) -> bool:
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        if not membership or membership.status not in ("active", "invited"):
            return False
        role_hierarchy = ["viewer", "editor", "admin", "owner"]
        user_level = role_hierarchy.index(membership.role) if membership.role in role_hierarchy else 0
        required_level = role_hierarchy.index(min_role) if min_role in role_hierarchy else 0
        return user_level >= required_level


abac = ABACEnforcer()
