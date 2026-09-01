"""Enterprise RBAC — Role-Based Access Control enforcement."""

from typing import Optional

from .models import ORG_ROLES, WORKSPACE_ROLES
from .service import org_service


class RBACEnforcer:
    """Enforce role-based access control across organizations and workspaces."""

    @staticmethod
    def has_org_permission(user_id: str, organization_id: str, permission: str) -> bool:
        """Check if a user has a specific permission in an organization."""
        membership = org_service.get_membership(organization_id, user_id)
        if not membership or membership.status != "active":
            return False

        role_perms = ORG_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    @staticmethod
    def has_workspace_permission(user_id: str, workspace_id: str, permission: str) -> bool:
        """Check if a user has a specific permission in a workspace."""
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        if not membership or membership.status != "active":
            return False

        role_perms = WORKSPACE_ROLES.get(membership.role, {}).get("permissions", [])
        return permission in role_perms

    @staticmethod
    def get_org_role(user_id: str, organization_id: str) -> Optional[str]:
        """Get a user's role in an organization."""
        membership = org_service.get_membership(organization_id, user_id)
        return membership.role if membership and membership.status == "active" else None

    @staticmethod
    def get_workspace_role(user_id: str, workspace_id: str) -> Optional[str]:
        """Get a user's role in a workspace."""
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        return membership.role if membership and membership.status == "active" else None

    @staticmethod
    def can_manage_member(manager_id: str, target_id: str, organization_id: str) -> bool:
        """Check if manager can manage target member (can't manage equal/higher roles)."""
        manager_membership = org_service.get_membership(organization_id, manager_id)
        target_membership = org_service.get_membership(organization_id, target_id)

        if not manager_membership or not target_membership:
            return False

        role_hierarchy = ["guest", "member", "manager", "admin", "owner"]
        manager_level = role_hierarchy.index(manager_membership.role) if manager_membership.role in role_hierarchy else 0
        target_level = role_hierarchy.index(target_membership.role) if target_membership.role in role_hierarchy else 0

        return manager_level > target_level

    @staticmethod
    def require_org_role(user_id: str, organization_id: str, min_role: str) -> bool:
        """Check if user has at least the minimum role in an organization."""
        membership = org_service.get_membership(organization_id, user_id)
        if not membership or membership.status != "active":
            return False

        role_hierarchy = ["guest", "member", "manager", "admin", "owner"]
        user_level = role_hierarchy.index(membership.role) if membership.role in role_hierarchy else 0
        required_level = role_hierarchy.index(min_role) if min_role in role_hierarchy else 0

        return user_level >= required_level

    @staticmethod
    def require_workspace_role(user_id: str, workspace_id: str, min_role: str) -> bool:
        """Check if user has at least the minimum role in a workspace."""
        membership = org_service.get_workspace_membership(workspace_id, user_id)
        if not membership or membership.status != "active":
            return False

        role_hierarchy = ["viewer", "editor", "admin", "owner"]
        user_level = role_hierarchy.index(membership.role) if membership.role in role_hierarchy else 0
        required_level = role_hierarchy.index(min_role) if min_role in role_hierarchy else 0

        return user_level >= required_level


rbac = RBACEnforcer()
