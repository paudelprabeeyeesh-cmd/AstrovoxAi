"""Immutable audit logging with export and filtering."""
import json
import time
import uuid
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    event_id: str
    actor: str
    action: str
    target: str
    outcome: str
    timestamp: float = field(default_factory=time.time)
    ip: Optional[str] = None
    severity: AuditSeverity = AuditSeverity.INFO
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "ip": self.ip,
            "severity": self.severity.value,
            "metadata": self.metadata,
        }


class AuditLogger:
    def __init__(self, capacity: int = 10000, path: Optional[str] = None):
        self._events: List[AuditEvent] = []
        self._capacity = capacity
        self._lock = threading.RLock()
        self._path = path
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def record(
        self,
        actor: str,
        action: str,
        target: str,
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            severity=severity,
            ip=ip,
            metadata=metadata or {},
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._capacity:
                self._events = self._events[-self._capacity:]
            if self._path:
                try:
                    with open(self._path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(event.to_dict(), default=str) + "\n")
                except Exception:
                    pass
        return event

    def query(self, actor: Optional[str] = None, action: Optional[str] = None, limit: int = 100) -> List[AuditEvent]:
        with self._lock:
            events = list(reversed(self._events))
        if actor:
            events = [e for e in events if e.actor == actor]
        if action:
            events = [e for e in events if e.action == action]
        return events[:limit]

    def get_failed_logins(self, since: float = 86400) -> List[AuditEvent]:
        cutoff = time.time() - since
        with self._lock:
            return [e for e in self._events if e.action == "auth_login" and e.outcome == "failed" and e.timestamp >= cutoff]

    def export(self, fmt: str = "json") -> str:
        with self._lock:
            data = [e.to_dict() for e in self._events]
        if fmt == "json":
            return json.dumps(data, indent=2, default=str)
        return ""


import os
audit_logger = AuditLogger(path=os.getenv("ASTROVOX_AUDIT_PATH"))
