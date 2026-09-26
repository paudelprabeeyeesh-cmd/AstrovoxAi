"""RBAC enforcement for organizations and workspaces."""

from typing import Any, Optional

from .models import ORG_ROLES, WORKSPACE_ROLES
from .service import org_service


class RBAC:
    def has_org_permission(self, user_id: str, org_id: str, permission: str) -> bool:
        membership = org_service.get_membership(org_id, user_id)
        if not membership:
            return False
        role_perms = ORG_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    def has_workspace_permission(self, user_id: str, ws_id: str, permission: str) -> bool:
        ws = org_service.get_workspace(ws_id)
        if not ws:
            return False
        membership = org_service.get_workspace_membership(ws_id, user_id)
        if not membership:
            return False
        role_perms = WORKSPACE_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    def can_manage_member(self, actor_id: str, target_id: str, org_id: str) -> bool:
        actor_perm = self.has_org_permission(actor_id, org_id, "member:manage")
        target_is_owner = org_service.get_membership(org_id, target_id) and org_service.get_membership(org_id, target_id).role == "owner"
        return actor_perm and not target_is_owner and actor_id != target_id

    def require_org_role(self, user_id: str, org_id: str, min_role: str) -> bool:
        hierarchy = ["guest", "member", "manager", "admin", "owner"]
        membership = org_service.get_membership(org_id, user_id)
        if not membership:
            return False
        return hierarchy.index(membership.role) >= hierarchy.index(min_role)


rbac = RBAC()
