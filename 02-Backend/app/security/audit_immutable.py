"""Immutable audit log store with append-only semantics and hash chaining.

Every entry is chained to the previous entry via SHA-256, providing
cryptographic evidence that the log has not been tampered with.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    id: str
    actor: str
    action: str
    target: str
    outcome: str
    metadata: str
    created_at: str
    prev_hash: str
    entry_hash: str


class ImmutableAuditStore:
    """Append-only audit log with hash-chain verification."""

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()

    def _compute_hash(self, entry_id: str, actor: str, action: str, target: str,
                      outcome: str, metadata: str, created_at: str, prev_hash: str) -> str:
        raw = f"{entry_id}|{actor}|{action}|{target}|{outcome}|{metadata}|{created_at}|{prev_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        outcome: str,
        metadata: str = "",
    ) -> AuditEntry:
        import uuid
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            prev_hash = self._entries[-1].entry_hash if self._entries else ""
            entry_id = str(uuid.uuid4())
            entry_hash = self._compute_hash(entry_id, actor, action, target, outcome, metadata, now, prev_hash)
            entry = AuditEntry(
                id=entry_id,
                actor=actor,
                action=action,
                target=target,
                outcome=outcome,
                metadata=metadata,
                created_at=now,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            self._entries.append(entry)
            return entry

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        with self._lock:
            for i, entry in enumerate(self._entries):
                expected_prev = self._entries[i - 1].entry_hash if i > 0 else ""
                if entry.prev_hash != expected_prev:
                    return False, i
                recalculated = self._compute_hash(
                    entry.id, entry.actor, entry.action, entry.target,
                    entry.outcome, entry.metadata, entry.created_at, entry.prev_hash,
                )
                if recalculated != entry.entry_hash:
                    return False, i
            return True, None

    def query(self, *, actor: Optional[str] = None, action: Optional[str] = None,
              outcome: Optional[str] = None, limit: int = 100) -> List[AuditEntry]:
        with self._lock:
            results = list(reversed(self._entries))
        if actor:
            results = [e for e in results if e.actor == actor]
        if action:
            results = [e for e in results if e.action == action]
        if outcome:
            results = [e for e in results if e.outcome == outcome]
        return results[:limit]

    def count(self) -> int:
        with self._lock:
            return len(self._entries)


immutable_audit_store = ImmutableAuditStore()
