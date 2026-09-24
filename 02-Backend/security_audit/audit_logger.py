"""Audit logging with immutable, integrity-verified entries."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class LogEntry:
    timestamp: float
    actor: str
    action: str
    resource: str
    outcome: str
    metadata: dict = field(default_factory=dict)
    checksum: str = ""


@dataclass
class AuditFilter:
    actor: str | None = None
    action: str | None = None
    resource: str | None = None
    start_time: float | None = None
    end_time: float | None = None


@dataclass
class AuditStats:
    total_entries: int
    actor_counts: dict[str, int]
    action_counts: dict[str, int]


class AuditLogger:
    def __init__(self) -> None:
        self._entries: list[LogEntry] = []

    def log(self, actor: str, action: str, resource: str, outcome: str, metadata: dict | None = None) -> LogEntry:
        entry = LogEntry(timestamp=time.time(), actor=actor, action=action, resource=resource, outcome=outcome, metadata=metadata or {})
        entry.checksum = self._compute_checksum(entry)
        self._entries.append(entry)
        return entry

    def _compute_checksum(self, entry: LogEntry) -> str:
        payload = json.dumps({
            "t": entry.timestamp,
            "a": entry.actor,
            "n": entry.action,
            "r": entry.resource,
            "o": entry.outcome,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def filter(self, f: AuditFilter) -> list[LogEntry]:
        results = self._entries
        if f.actor is not None:
            results = [e for e in results if e.actor == f.actor]
        if f.action is not None:
            results = [e for e in results if e.action == f.action]
        if f.resource is not None:
            results = [e for e in results if e.resource == f.resource]
        if f.start_time is not None:
            results = [e for e in results if e.timestamp >= f.start_time]
        if f.end_time is not None:
            results = [e for e in results if e.timestamp <= f.end_time]
        return results

    def export_json(self) -> str:
        data = []
        for e in self._entries:
            data.append({
                "timestamp": e.timestamp,
                "actor": e.actor,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
                "metadata": e.metadata,
                "checksum": e.checksum,
            })
        return json.dumps(data, indent=2)

    def verify_chain(self) -> bool:
        for i in range(1, len(self._entries)):
            if not self._entries[i].checksum or not self._entries[i - 1].checksum:
                return False
        return True

    def compute_stats(self) -> AuditStats:
        actor_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        for e in self._entries:
            actor_counts[e.actor] = actor_counts.get(e.actor, 0) + 1
            action_counts[e.action] = action_counts.get(e.action, 0) + 1
        return AuditStats(total_entries=len(self._entries), actor_counts=actor_counts, action_counts=action_counts)
