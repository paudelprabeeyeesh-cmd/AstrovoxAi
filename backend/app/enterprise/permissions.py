"""Fine-grained permissions with conditions, inheritance, and resource-level access."""

import logging
from typing import Any, Dict, List, Optional

from .models import ORG_ROLES, WORKSPACE_ROLES
from .service import org_service

logger = logging.getLogger(__name__)


class PermissionGrant:
    def __init__(self, grant_id: str, user_id: str, resource: str, action: str, effect: str = "allow", conditions: Optional[Dict[str, Any]] = None):
        self.grant_id = grant_id
        self.user_id = user_id
        self.resource = resource
        self.action = action
        self.effect = effect
        self.conditions = conditions or {}

    def matches(self, resource: str, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if self.resource != resource or self.action != action:
            return False
        ctx = context or {}
        for key, value in self.conditions.items():
            if key not in ctx:
                return False
            if isinstance(value, dict):
                if "in" in value and ctx[key] not in value["in"]:
                    return False
                if "eq" in value and ctx[key] != value["eq"]:
                    return False
                if "neq" in value and ctx[key] == value["neq"]:
                    return False
            else:
                if ctx[key] != value:
                    return False
        return True


class FineGrainedPermissions:
    def __init__(self):
        self._grants: Dict[str, List[PermissionGrant]] = {}
        self._inheritance: Dict[str, List[str]] = {}

    def grant(self, user_id: str, resource: str, action: str, effect: str = "allow", conditions: Optional[Dict[str, Any]] = None, org_id: Optional[str] = None) -> PermissionGrant:
        grant_id = f"grant_{uuid.uuid4().hex[:12]}"
        grant = PermissionGrant(grant_id, user_id, resource, action, effect, conditions)
        key = org_id or "global"
        self._grants.setdefault(key, []).append(grant)
        logger.info("Granted %s %s on %s for user %s in %s", effect, action, resource, user_id, key)
        return grant

    def revoke(self, grant_id: str, org_id: Optional[str] = None) -> bool:
        key = org_id or "global"
        grants = self._grants.get(key, [])
        for i, g in enumerate(grants):
            if g.grant_id == grant_id:
                del grants[i]
                return True
        return False

    def check(self, user_id: str, resource: str, action: str, context: Optional[Dict[str, Any]] = None, org_id: Optional[str] = None) -> bool:
        key = org_id or "global"
        grants = self._grants.get(key, [])
        for grant in grants:
            if grant.user_id == user_id and grant.matches(resource, action, context):
                return grant.effect == "allow"
        return False

    def list_grants(self, user_id: str, org_id: Optional[str] = None) -> List[dict]:
        key = org_id or "global"
        return [
            {
                "grant_id": g.grant_id,
                "resource": g.resource,
                "action": g.action,
                "effect": g.effect,
                "conditions": g.conditions,
            }
            for g in self._grants.get(key, [])
            if g.user_id == user_id
        ]

    def set_inheritance(self, parent_resource: str, child_resource: str) -> None:
        self._inheritance.setdefault(parent_resource, []).append(child_resource)

    def get_effective_permissions(self, user_id: str, org_id: Optional[str] = None) -> List[str]:
        key = org_id or "global"
        perms = set()
        for grant in self._grants.get(key, []):
            if grant.user_id == user_id and grant.effect == "allow":
                perms.add(f"{grant.resource}:{grant.action}")
        return sorted(perms)


fine_permissions = FineGrainedPermissions()
