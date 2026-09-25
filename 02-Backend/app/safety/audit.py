"""Safety audit logging."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyAuditEntry:
    id: str
    timestamp: float
    event_type: str
    user_id: Optional[str]
    session_id: Optional[str]
    model_id: Optional[str]
    severity: str
    action: str
    details: dict
    metadata: dict = field(default_factory=dict)

    @property
    def iso_timestamp(self) -> str:
        return datetime.utcfromtimestamp(self.timestamp).isoformat() + "Z"


class SafetyAuditLogger:
    """Log safety-related events for compliance and forensics."""

    EVENT_TYPES = [
        "prompt_injection_detected",
        "jailbreak_detected",
        "pii_redacted",
        "content_blocked",
        "content_flagged",
        "moderation_escalated",
        "human_review_requested",
        "human_review_completed",
        "feedback_submitted",
        "incident_created",
        "incident_resolved",
        "red_team_run",
        "evaluation_run",
        "policy_violation",
        "threshold_breach",
        "model_behavior_anomaly",
    ]

    def __init__(self, max_entries: int = 100000):
        self._entries: list[SafetyAuditEntry] = []
        self._max_entries = max_entries

    def log(
        self,
        event_type: str,
        severity: str,
        action: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        model_id: Optional[str] = None,
        details: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> SafetyAuditEntry:
        if event_type not in self.EVENT_TYPES:
            logger.warning("Unknown audit event type: %s", event_type)
        entry = SafetyAuditEntry(
            id=str(uuid.uuid4())[:12],
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            session_id=session_id,
            model_id=model_id,
            severity=severity,
            action=action,
            details=details or {},
            metadata=metadata or {},
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        logger.info("AUDIT %s: %s", event_type, entry.id)
        return entry

    def log_injection(self, user_id: Optional[str], session_id: Optional[str], details: dict):
        return self.log(
            event_type="prompt_injection_detected",
            severity="high",
            action="block",
            user_id=user_id,
            session_id=session_id,
            details=details,
        )

    def log_jailbreak(self, user_id: Optional[str], session_id: Optional[str], details: dict):
        return self.log(
            event_type="jailbreak_detected",
            severity="critical",
            action="block_alert",
            user_id=user_id,
            session_id=session_id,
            details=details,
        )

    def log_pii(self, user_id: Optional[str], session_id: Optional[str], details: dict):
        return self.log(
            event_type="pii_redacted",
            severity="high",
            action="redact",
            user_id=user_id,
            session_id=session_id,
            details=details,
        )

    def log_moderation(self, user_id: Optional[str], session_id: Optional[str], model_id: Optional[str], details: dict):
        return self.log(
            event_type=details.get("event", "content_blocked"),
            severity=details.get("severity", "medium"),
            action=details.get("action", "flag"),
            user_id=user_id,
            session_id=session_id,
            model_id=model_id,
            details=details,
        )

    def get_entries(self, limit: int = 100, event_type: Optional[str] = None, severity: Optional[str] = None) -> list[SafetyAuditEntry]:
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if severity:
            entries = [e for e in entries if e.severity == severity]
        return entries[-limit:]

    def get_events_summary(self) -> dict:
        summary = {}
        for entry in self._entries:
            summary[entry.event_type] = summary.get(entry.event_type, 0) + 1
        return summary

    def export_log(self, since: Optional[float] = None, limit: int = 1000) -> list[dict]:
        entries = self._entries
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return [
            {
                "id": e.id,
                "timestamp": e.iso_timestamp,
                "event_type": e.event_type,
                "user_id": e.user_id,
                "session_id": e.session_id,
                "model_id": e.model_id,
                "severity": e.severity,
                "action": e.action,
                "details": e.details,
            }
            for e in entries[-limit:]
        ]


safety_audit_logger = SafetyAuditLogger()
