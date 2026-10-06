"""Role-based authorization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Role:
    """A role definition."""
    name: str
    permissions: list[str] = field(default_factory=list)


@dataclass
class UserRole:
    """A user-role assignment."""
    user_id: str
    roles: list[str] = field(default_factory=list)


class Authorization:
    """Role-based access control."""

    def __init__(self):
        self.roles: dict[str, Role] = {}
        self.users: dict[str, UserRole] = {}

    def create_role(self, name: str, permissions: list[str] | None = None) -> Role:
        self.roles[name] = Role(name=name, permissions=list(permissions or []))
        return self.roles[name]

    def assign_role(self, user_id: str, role: str) -> bool:
        if role not in self.roles:
            return False
        u = self.users.setdefault(user_id, UserRole(user_id=user_id))
        if role not in u.roles:
            u.roles.append(role)
        return True

    def has_permission(self, user_id: str, permission: str) -> bool:
        u = self.users.get(user_id)
        if u is None:
            return False
        for role in u.roles:
            r = self.roles.get(role)
            if r and permission in r.permissions:
                return True
        return False

    def authorize(self, user_id: str, required: list[str]) -> bool:
        return all(self.has_permission(user_id, p) for p in required)

    def list_user_roles(self, user_id: str) -> list[str]:
        u = self.users.get(user_id)
        return u.roles if u else []
