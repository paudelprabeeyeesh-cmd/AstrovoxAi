"""Enterprise models — organizations, workspaces, memberships, roles, permissions."""

from dataclasses import dataclass, field
from typing import Optional
import time
import uuid


@dataclass
class Organization:
    id: str
    name: str
    slug: str
    description: str = ""
    website: str = ""
    logo_url: str = ""
    owner_id: str = ""
    settings: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    member_count: int = 0
    workspace_count: int = 0


@dataclass
class Workspace:
    id: str
    organization_id: str
    name: str
    slug: str
    description: str = ""
    type: str = "team"
    owner_id: str = ""
    settings: dict = field(default_factory=dict)
    is_active: bool = True
    is_archived: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    member_count: int = 0


@dataclass
class OrganizationMembership:
    id: str
    organization_id: str
    user_id: str
    role: str = "member"
    status: str = "active"
    invited_by: str = ""
    joined_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class WorkspaceMembership:
    id: str
    workspace_id: str
    user_id: str
    role: str = "viewer"
    permissions: list = field(default_factory=list)
    status: str = "active"
    joined_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class Role:
    id: str
    organization_id: str
    name: str
    description: str = ""
    permissions: list = field(default_factory=list)
    is_system: bool = False
    created_at: float = field(default_factory=time.time)


@dataclass
class Permission:
    id: str
    name: str
    description: str = ""
    resource: str = ""
    action: str = ""


ORG_ROLES = {
    "owner": {
        "description": "Full organization control",
        "permissions": [
            "org:read", "org:write", "org:delete",
            "workspace:create", "workspace:read", "workspace:write", "workspace:delete",
            "member:invite", "member:remove", "member:manage",
            "billing:manage", "settings:manage",
        ],
    },
    "admin": {
        "description": "Organization administration",
        "permissions": [
            "org:read", "org:write",
            "workspace:create", "workspace:read", "workspace:write",
            "member:invite", "member:remove",
            "settings:manage",
        ],
    },
    "manager": {
        "description": "Team management",
        "permissions": [
            "org:read",
            "workspace:create", "workspace:read", "workspace:write",
            "member:invite",
        ],
    },
    "member": {
        "description": "Standard member",
        "permissions": [
            "org:read",
            "workspace:read", "workspace:write",
        ],
    },
    "guest": {
        "description": "Limited access",
        "permissions": [
            "org:read",
            "workspace:read",
        ],
    },
}

WORKSPACE_ROLES = {
    "owner": {
        "description": "Full workspace control",
        "permissions": [
            "workspace:read", "workspace:write", "workspace:delete",
            "member:invite", "member:remove", "member:manage",
            "document:create", "document:read", "document:write", "document:delete",
            "conversation:create", "conversation:read", "conversation:write", "conversation:delete",
            "agent:create", "agent:read", "agent:write", "agent:delete",
        ],
    },
    "admin": {
        "description": "Workspace administration",
        "permissions": [
            "workspace:read", "workspace:write",
            "member:invite", "member:remove",
            "document:create", "document:read", "document:write",
            "conversation:create", "conversation:read", "conversation:write",
            "agent:create", "agent:read", "agent:write",
        ],
    },
    "editor": {
        "description": "Can edit content",
        "permissions": [
            "workspace:read",
            "document:create", "document:read", "document:write",
            "conversation:create", "conversation:read", "conversation:write",
            "agent:read",
        ],
    },
    "viewer": {
        "description": "Read-only access",
        "permissions": [
            "workspace:read",
            "document:read",
            "conversation:read",
            "agent:read",
        ],
    },
}
