"""Permission auditing and access control verification."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class Permission:
    name: str
    resource: str
    actions: list[str] = field(default_factory=list)


@dataclass
class Role:
    name: str
    permissions: list[Permission] = field(default_factory=list)


@dataclass
class AccessAuditResult:
    user: str
    role: str
    permission: str
    granted: bool
    reason: str


class PermissionAuditor:
    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._audit_log: list[AccessAuditResult] = []

    def create_role(self, name: str, permissions: Sequence[Permission] | None = None) -> Role:
        role = Role(name=name, permissions=list(permissions or []))
        self._roles[name] = role
        return role

    def grant(self, role_name: str, permission: Permission) -> None:
        if role_name not in self._roles:
            self._roles[role_name] = Role(name=role_name)
        if permission not in self._roles[role_name].permissions:
            self._roles[role_name].permissions.append(permission)

    def revoke(self, role_name: str, permission: Permission) -> None:
        if role_name in self._roles:
            self._roles[role_name].permissions = [p for p in self._roles[role_name].permissions if p != permission]

    def audit_access(self, user: str, role_name: str, permission_name: str) -> AccessAuditResult:
        role = self._roles.get(role_name)
        if role is None:
            result = AccessAuditResult(user=user, role=role_name, permission=permission_name, granted=False, reason="role_not_found")
        else:
            granted = any(p.name == permission_name for p in role.permissions)
            reason = "granted" if granted else "permission_denied"
            result = AccessAuditResult(user=user, role=role_name, permission=permission_name, granted=granted, reason=reason)
        self._audit_log.append(result)
        return result

    def get_role_permissions(self, role_name: str) -> list[Permission]:
        role = self._roles.get(role_name)
        return list(role.permissions) if role else []

    def generate_matrix(self) -> dict[str, list[str]]:
        return {name: [p.name for p in role.permissions] for name, role in self._roles.items()}

    def get_audit_log(self) -> list[AccessAuditResult]:
        return list(self._audit_log)
