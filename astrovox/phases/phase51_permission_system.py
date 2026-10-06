"""Plugin permission system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Permission:
    """A single permission."""
    name: str
    resource: str = "*"
    action: str = "*"

    def to_dict(self) -> dict:
        return {"name": self.name, "resource": self.resource, "action": self.action}


class PermissionSystem:
    """Permission model for plugins."""

    def __init__(self):
        self.allows: dict[tuple[str, str], set[str]] = {}
        self.denies: set[tuple[str, str]] = set()

    def grant(self, plugin: str, permission: Permission) -> None:
        key = (plugin, permission.resource)
        self.allows.setdefault(key, set()).add(permission.action)

    def revoke(self, plugin: str, permission: Permission) -> None:
        key = (plugin, permission.resource)
        self.allows.get(key, set()).discard(permission.action)

    def check(self, plugin: str, resource: str, action: str) -> bool:
        key = (plugin, resource)
        if key in self.denies:
            return False
        actions = self.allows.get(key)
        if actions is None:
            return False
        return action in actions

    def has_any(self, plugin: str, resources: list[str], action: str) -> bool:
        for r in resources:
            if self.check(plugin, r, action):
                return True
        return False

    def deny(self, plugin: str, resource: str) -> None:
        self.denies.add((plugin, resource))
