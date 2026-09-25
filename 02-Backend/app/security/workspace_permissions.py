"""Workspace permissions and multi-tenancy."""

from typing import Dict, Optional, Any, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class WorkspaceRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class WorkspacePermission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_SETTINGS = "manage_settings"
    VIEW_ANALYTICS = "view_analytics"
    BILLING = "billing"


WORKSPACE_ROLE_PERMISSIONS: Dict[WorkspaceRole, Set[WorkspacePermission]] = {
    WorkspaceRole.OWNER: set(WorkspacePermission),
    WorkspaceRole.ADMIN: {
        WorkspacePermission.READ,
        WorkspacePermission.WRITE,
        WorkspacePermission.DELETE,
        WorkspacePermission.MANAGE_MEMBERS,
        WorkspacePermission.VIEW_ANALYTICS,
    },
    WorkspaceRole.MEMBER: {WorkspacePermission.READ, WorkspacePermission.WRITE},
    WorkspaceRole.VIEWER: {WorkspacePermission.READ},
}


@dataclass
class WorkspaceMember:
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    invited_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkspaceManager:
    _workspaces: Dict[str, Dict[str, WorkspaceMember]] = {}

    @classmethod
    def add_member(cls, workspace_id: str, member: WorkspaceMember) -> None:
        if workspace_id not in cls._workspaces:
            cls._workspaces[workspace_id] = {}
        cls._workspaces[workspace_id][member.user_id] = member

    @classmethod
    def remove_member(cls, workspace_id: str, user_id: str) -> None:
        if workspace_id in cls._workspaces:
            cls._workspaces[workspace_id].pop(user_id, None)

    @classmethod
    def get_member(cls, workspace_id: str, user_id: str) -> Optional[WorkspaceMember]:
        return cls._workspaces.get(workspace_id, {}).get(user_id)

    @classmethod
    def list_members(cls, workspace_id: str) -> List[WorkspaceMember]:
        return list(cls._workspaces.get(workspace_id, {}).values())

    @classmethod
    def has_permission(cls, workspace_id: str, user_id: str, permission: WorkspacePermission) -> bool:
        member = cls.get_member(workspace_id, user_id)
        if not member:
            return False
        permissions = WORKSPACE_ROLE_PERMISSIONS.get(member.role, set())
        return permission in permissions
