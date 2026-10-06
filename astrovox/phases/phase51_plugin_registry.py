"""Plugin registry for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Plugin:
    """A registered plugin."""
    id: str
    name: str
    version: str
    description: str = ""
    permissions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "version": self.version,
                "description": self.description, "permissions": self.permissions}


class PluginRegistry:
    """Plugin catalog."""

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}

    def register(self, name: str, version: str, description: str = "",
                 permissions: list[str] | None = None) -> Plugin:
        pid = f"plugin_{len(self.plugins)}"
        p = Plugin(id=pid, name=name, version=version, description=description,
                   permissions=list(permissions or []))
        self.plugins[pid] = p
        return p

    def get(self, pid: str) -> Plugin | None:
        return self.plugins.get(pid)

    def list_plugins(self) -> list[Plugin]:
        return list(self.plugins.values())

    def search(self, query: str) -> list[Plugin]:
        q = query.lower()
        return [p for p in self.plugins.values() if q in p.name.lower() or q in p.description.lower()]

    def count(self) -> int:
        return len(self.plugins)
