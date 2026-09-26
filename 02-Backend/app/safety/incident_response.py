"""Incident response for AI failures."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class AIFailureIncident:
    id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    model_id: Optional[str]
    affected_users: int
    root_cause: str = ""
    remediation: str = ""
    created_by: str = "system"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class IncidentTimelineEntry:
    incident_id: str
    timestamp: float
    action: str
    actor: str
    details: str


class IncidentResponse:
    """Manage AI failure incidents and response workflows."""

    RESPONSE_PLAYBOOKS = {
        "prompt_injection_breach": {
            "severity": IncidentSeverity.HIGH,
            "steps": [
                "Isolate affected model endpoints",
                "Review audit logs for attack vectors",
                "Update injection detection patterns",
                "Notify security team",
                "Deploy patch within 24 hours",
            ],
        },
        "jailbreak_success": {
            "severity": IncidentSeverity.CRITICAL,
            "steps": [
                "Immediately disable affected model variant",
                "Audit recent outputs for harmful content",
                "Notify leadership and compliance",
                "Initiate red team exercise",
                "Review and harden jailbreak defenses",
            ],
        },
        "pii_leak": {
            "severity": IncidentSeverity.CRITICAL,
            "steps": [
                "Stop affected data pipeline",
                "Assess scope of leaked PII",
                "Notify affected users within 72 hours",
                "Report to data protection authority if required",
                "Review and enhance PII detection",
            ],
        },
        "harmful_output": {
            "severity": IncidentSeverity.HIGH,
            "steps": [
                "Remove harmful content",
                "Review user who received content",
                "Update content moderation filters",
                "Document for training data review",
                "Escalate to safety team",
            ],
        },
        "model_degradation": {
            "severity": IncidentSeverity.MEDIUM,
            "steps": [
                "Compare current metrics to baseline",
                "Identify changed inputs or configs",
                "Roll back to last known good version",
                "Investigate root cause",
                "Update monitoring thresholds",
            ],
        },
        "bias_incident": {
            "severity": IncidentSeverity.HIGH,
            "steps": [
                "Quarantine affected model outputs",
                "Review fairness metrics",
                "Engage AI ethics team",
                "Communicate with affected communities",
                "Plan model retraining",
            ],
        },
    }

    def __init__(self):
        self._incidents: dict[str, AIFailureIncident] = {}
        self._timeline: list[IncidentTimelineEntry] = []

    def create_incident(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        model_id: Optional[str] = None,
        affected_users: int = 0,
        incident_type: Optional[str] = None,
        created_by: str = "system",
    ) -> AIFailureIncident:
        incident = AIFailureIncident(
            id=f"INC-{int(time.time())}-{uuid.uuid4().hex[:6]}",
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            model_id=model_id,
            affected_users=affected_users,
            created_by=created_by,
        )
        self._incidents[incident.id] = incident
        self._add_timeline(incident.id, "created", created_by, f"Incident created: {title}")
        if incident_type and incident_type in self.RESPONSE_PLAYBOOKS:
            playbook = self.RESPONSE_PLAYBOOKS[incident_type]
            incident.metadata["playbook"] = incident_type
            self._add_timeline(incident.id, "playbook_assigned", "system", f"Assigned playbook: {incident_type}")
        logger.warning("INCIDENT CREATED: %s - %s", incident.id, title)
        return incident

    def get_incident(self, incident_id: str) -> Optional[AIFailureIncident]:
        return self._incidents.get(incident_id)

    def update_status(self, incident_id: str, status: IncidentStatus, actor: str = "system"):
        incident = self._incidents.get(incident_id)
        if not incident:
            return False
        incident.status = status
        incident.updated_at = time.time()
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = time.time()
        self._add_timeline(incident_id, "status_update", actor, f"Status changed to {status.value}")
        logger.info("INCIDENT %s: status -> %s", incident_id, status.value)
        return True

    def add_remediation(self, incident_id: str, root_cause: str, remediation: str, actor: str = "system"):
        incident = self._incidents.get(incident_id)
        if not incident:
            return False
        incident.root_cause = root_cause
        incident.remediation = remediation
        incident.updated_at = time.time()
        self._add_timeline(incident_id, "remediation_added", actor, f"Root cause: {root_cause}")
        return True

    def get_timeline(self, incident_id: str) -> list[IncidentTimelineEntry]:
        return [t for t in self._timeline if t.incident_id == incident_id]

    def get_open_incidents(self) -> list[AIFailureIncident]:
        return [i for i in self._incidents.values() if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)]

    def get_incidents_by_severity(self, severity: IncidentSeverity) -> list[AIFailureIncident]:
        return [i for i in self._incidents.values() if i.severity == severity]

    def get_summary(self) -> dict:
        incidents = list(self._incidents.values())
        return {
            "total_incidents": len(incidents),
            "open": sum(1 for i in incidents if i.status == IncidentStatus.OPEN),
            "investigating": sum(1 for i in incidents if i.status == IncidentStatus.INVESTIGATING),
            "resolved": sum(1 for i in incidents if i.status == IncidentStatus.RESOLVED),
            "by_severity": {
                sev.value: sum(1 for i in incidents if i.severity == sev)
                for sev in IncidentSeverity
            },
        }

    def _add_timeline(self, incident_id: str, action: str, actor: str, details: str):
        self._timeline.append(IncidentTimelineEntry(
            incident_id=incident_id,
            timestamp=time.time(),
            action=action,
            actor=actor,
            details=details,
        ))


incident_response = IncidentResponse()
