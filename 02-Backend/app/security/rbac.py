"""Role-Based Access Control (RBAC)."""

from typing import Dict, Set
from dataclasses import dataclass, field
from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"
    DEVELOPER = "developer"


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_BILLING = "manage_billing"


@dataclass
class RoleDefinition:
    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    inherits: Set[Role] = field(default_factory=set)


ROLE_DEFINITIONS: Dict[Role, RoleDefinition] = {
    Role.ADMIN: RoleDefinition(
        role=Role.ADMIN,
        permissions=set(Permission),
    ),
    Role.MODERATOR: RoleDefinition(
        role=Role.MODERATOR,
        permissions={Permission.READ, Permission.WRITE, Permission.DELETE},
        inherits={Role.USER},
    ),
    Role.DEVELOPER: RoleDefinition(
        role=Role.DEVELOPER,
        permissions={Permission.READ, Permission.WRITE, Permission.VIEW_ANALYTICS},
        inherits={Role.USER},
    ),
    Role.USER: RoleDefinition(
        role=Role.USER,
        permissions={Permission.READ, Permission.WRITE},
    ),
    Role.GUEST: RoleDefinition(
        role=Role.GUEST,
        permissions={Permission.READ},
    ),
}


class RBACManager:
    _user_roles: Dict[str, Set[Role]] = {}

    @classmethod
    def assign_role(cls, user_id: str, role: Role) -> None:
        if user_id not in cls._user_roles:
            cls._user_roles[user_id] = set()
        cls._user_roles[user_id].add(role)

    @classmethod
    def revoke_role(cls, user_id: str, role: Role) -> None:
        if user_id in cls._user_roles:
            cls._user_roles[user_id].discard(role)

    @classmethod
    def get_roles(cls, user_id: str) -> Set[Role]:
        return cls._user_roles.get(user_id, set())

    @classmethod
    def has_permission(cls, user_id: str, permission: Permission) -> bool:
        roles = cls.get_roles(user_id)
        effective_permissions: Set[Permission] = set()
        for role in roles:
            definition = ROLE_DEFINITIONS.get(role)
            if definition:
                effective_permissions.update(definition.permissions)
                for inherited_role in definition.inherits:
                    inherited = ROLE_DEFINITIONS.get(inherited_role)
                    if inherited:
                        effective_permissions.update(inherited.permissions)
        return permission in effective_permissions
