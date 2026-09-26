"""Incident response automation."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class IncidentStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IncidentResponder:
    def __init__(self) -> None:
        self._incidents: Dict[str, Incident] = {}

    def create_incident(self, title: str, severity: IncidentSeverity) -> Incident:
        incident_id = uuid.uuid4().hex
        incident = Incident(incident_id=incident_id, title=title, severity=severity)
        self._incidents[incident_id] = incident
        return incident

    def acknowledge(self, incident_id: str) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.INVESTIGATING
        return incident

    def resolve(self, incident_id: str) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if incident:
            incident.status = IncidentStatus.RESOLVED
        return incident


incident_responder = IncidentResponder()
