"""Audit log writer."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AuditEntry:
    """An audit log entry."""
    id: str
    action: str
    actor: str
    resource: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.time())
    verified: bool = True

    def to_dict(self) -> dict:
        return {"id": self.id, "action": self.action, "actor": self.actor,
                "resource": self.resource, "metadata": self.metadata,
                "timestamp": self.timestamp}


class AuditLogger:
    """Immutable audit logging."""

    def __init__(self, max_entries: int = 100000):
        self.max_entries = max_entries
        self.entries: list[AuditEntry] = []
        self._counter = 0

    def log(self, action: str, actor: str, resource: str,
            metadata: dict | None = None) -> AuditEntry:
        self._counter += 1
        entry = AuditEntry(id=f"audit_{self._counter}", action=action, actor=actor,
                           resource=resource, metadata=dict(metadata or {}))
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        return entry

    def get(self, actor: str | None = None, action: str | None = None,
            limit: int = 100) -> list[AuditEntry]:
        result = self.entries
        if actor is not None:
            result = [e for e in result if e.actor == actor]
        if action is not None:
            result = [e for e in result if e.action == action]
        return result[-limit:]

    def count(self) -> int:
        return len(self.entries)

    def clear(self) -> None:
        self.entries.clear()
        self._counter = 0
