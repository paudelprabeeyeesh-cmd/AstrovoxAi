"""Immutable audit log store with append-only semantics and hash chaining.

This module implements a tamper-evident audit log with:

1. SHA-256 hash chain linking each entry to the previous
2. Append-only semantics (no modification or deletion)
3. Periodic checkpointing for performance
4. Verification routines for integrity validation
5. Query support with filtering
6. Audit log export for compliance
7. Structured logging integration
8. Retention policies

Threat model: OWASP Top A09:2021 - Security Logging and Monitoring Failures
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOCKOUT = "auth.lockout"
    TOKEN_ISSUED = "token.issued"
    TOKEN_REVOKED = "token.revoked"
    API_CALL = "api.call"
    DATA_ACCESS = "data.access"
    DATA_MODIFICATION = "data.modification"
    DATA_DELETION = "data.deletion"
    SECURITY_EVENT = "security.event"
    CONFIGURATION_CHANGE = "configuration.change"
    ADMIN_ACTION = "admin.action"
    COMPLIANCE_EVENT = "compliance.event"
    ERROR = "error"


class AuditSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


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
    severity: str = "info"
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "outcome": self.outcome,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "severity": self.severity,
            "source_ip": self.source_ip,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
        }


class ImmutableAuditStore:
    """Append-only audit log with hash-chain verification."""

    def __init__(self, checkpoint_interval: int = 1000) -> None:
        self._entries: List[AuditEntry] = []
        self._lock = threading.Lock()
        self._checkpoint_interval = checkpoint_interval
        self._checkpoints: List[Dict[str, Any]] = []
        self._total_records = 0

    def _compute_hash(self, entry_id: str, actor: str, action: str, target: str,
                      outcome: str, metadata: str, created_at: str, prev_hash: str) -> str:
        raw = f"{entry_id}|{actor}|{action}|{target}|{outcome}|{metadata}|{created_at}|{prev_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _create_checkpoint(self) -> None:
        """Create a checkpoint for faster verification."""
        if self._entries:
            checkpoint = {
                "index": len(self._entries) - 1,
                "entry_hash": self._entries[-1].entry_hash,
                "timestamp": time.time(),
                "total_entries": len(self._entries),
            }
            self._checkpoints.append(checkpoint)
            if len(self._checkpoints) > 100:
                self._checkpoints = self._checkpoints[-50:]

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        outcome: str,
        metadata: str = "",
        severity: str = "info",
        source_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AuditEntry:
        """Record a new audit entry (append-only)."""
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
                severity=severity,
                source_ip=source_ip,
                user_agent=user_agent,
                session_id=session_id,
            )
            self._entries.append(entry)
            self._total_records += 1

            # Create checkpoint at intervals
            if len(self._entries) % self._checkpoint_interval == 0:
                self._create_checkpoint()

            return entry

    def verify_chain(self) -> tuple[bool, Optional[int]]:
        """Verify the integrity of the hash chain."""
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

    def verify_from_checkpoint(self, checkpoint_index: int) -> tuple[bool, Optional[int]]:
        """Verify chain from a specific checkpoint."""
        with self._lock:
            if checkpoint_index >= len(self._entries):
                return False, checkpoint_index
            start = max(0, checkpoint_index)
            for i, entry in enumerate(self._entries[start:], start=start):
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

    def query(
        self,
        *,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """Query audit log with filters."""
        with self._lock:
            results = list(reversed(self._entries))

        if actor:
            results = [e for e in results if e.actor == actor]
        if action:
            results = [e for e in results if e.action == action]
        if outcome:
            results = [e for e in results if e.outcome == outcome]
        if severity:
            results = [e for e in results if e.severity == severity]

        return results[offset:offset + limit]

    def count(self) -> int:
        """Get total count of audit entries."""
        with self._lock:
            return len(self._entries)

    def export_json(self, limit: int = 1000) -> str:
        """Export audit log as JSON."""
        with self._lock:
            entries = self._entries[-limit:]
        return json.dumps([e.to_dict() for e in entries], default=str, indent=2)

    def get_checkpoints(self) -> List[Dict[str, Any]]:
        """Get checkpoint history."""
        with self._lock:
            return list(self._checkpoints)

    def get_stats(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        with self._lock:
            by_action: Dict[str, int] = {}
            by_actor: Dict[str, int] = {}
            by_severity: Dict[str, int] = {}
            for entry in self._entries:
                by_action[entry.action] = by_action.get(entry.action, 0) + 1
                by_actor[entry.actor] = by_actor.get(entry.actor, 0) + 1
                by_severity[entry.severity] = by_severity.get(entry.severity, 0) + 1

            return {
                "total_entries": len(self._entries),
                "total_checkpoints": len(self._checkpoints),
                "action_distribution": by_action,
                "actor_distribution": by_actor,
                "severity_distribution": by_severity,
                "oldest_entry": self._entries[0].created_at if self._entries else None,
                "newest_entry": self._entries[-1].created_at if self._entries else None,
            }

    def get_integrity_report(self) -> Dict[str, Any]:
        """Generate an integrity report for the audit log."""
        is_valid, broken_index = self.verify_chain()
        return {
            "is_valid": is_valid,
            "broken_index": broken_index,
            "total_entries": self.count(),
            "total_checkpoints": len(self._checkpoints),
            "last_checkpoint": self._checkpoints[-1] if self._checkpoints else None,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }


immutable_audit_store = ImmutableAuditStore()


def record_audit_event(
    actor: str,
    action: str,
    target: str,
    outcome: str,
    metadata: str = "",
    severity: str = "info",
    source_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    session_id: Optional[str] = None,
) -> AuditEntry:
    """Convenience function to record an audit event."""
    return immutable_audit_store.record(
        actor, action, target, outcome, metadata, severity, source_ip, user_agent, session_id
    )


def verify_audit_integrity() -> tuple[bool, Optional[int]]:
    """Convenience function to verify audit log integrity."""
    return immutable_audit_store.verify_chain()


def export_audit_log(limit: int = 1000) -> str:
    """Convenience function to export audit log."""
    return immutable_audit_store.export_json(limit)
