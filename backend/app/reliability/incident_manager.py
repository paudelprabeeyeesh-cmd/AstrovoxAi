"""Incident lifecycle management."""
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class IncidentSeverity(Enum):
    P0 = "p0"
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"


class IncidentStatus(Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class Incident:
    id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.OPEN
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    description: str = ""
    owner: str = ""
    timeline: List[Dict[str, str]] = field(default_factory=list)

    def update_status(self, status: IncidentStatus):
        self.status = status
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.timeline.append({
            "at": self.updated_at,
            "action": f"status_changed_to_{status.value}",
        })


class IncidentManager:
    def __init__(self):
        self._incidents: Dict[str, Incident] = {}
        self._lock = threading.Lock()

    def create(self, title: str, severity: IncidentSeverity, description: str = "", owner: str = "") -> Incident:
        incident_id = f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{len(self._incidents)+1:03d}"
        incident = Incident(
            id=incident_id,
            title=title,
            severity=severity,
            description=description,
            owner=owner,
        )
        with self._lock:
            self._incidents[incident_id] = incident
        return incident

    def get(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def update_status(self, incident_id: str, status: IncidentStatus):
        incident = self._incidents.get(incident_id)
        if incident:
            incident.update_status(status)

    def list_active(self) -> List[Incident]:
        return [
            inc for inc in self._incidents.values()
            if inc.status not in (IncidentStatus.CLOSED, IncidentStatus.RESOLVED)
        ]
