"""Incident timeline visualizer with event sourcing, severity tracking, and MTTR analytics."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class IncidentSeverity(str, Enum):
    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPhase(str, Enum):
    DETECTION = "detection"
    TRIAGE = "triage"
    MITIGATION = "mitigation"
    RESOLUTION = "resolution"
    POSTMORTEM = "postmortem"


@dataclass
class TimelineEvent:
    event_id: str
    incident_id: str
    phase: IncidentPhase
    timestamp: datetime
    actor: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class Incident:
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detected_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    timeline: List[TimelineEvent] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    root_cause: str = ""
    owner: str = ""


class IncidentTimelineVisualizer:
    _incidents: Dict[str, Incident] = {}
    _lock = threading.RLock()
    _next_event_id = 1
    _next_incident_id = 1

    @classmethod
    def create_incident(
        cls,
        title: str,
        severity: IncidentSeverity,
        description: str = "",
        affected_services: Optional[List[str]] = None,
        owner: str = "",
        tags: Optional[List[str]] = None,
    ) -> Incident:
        with cls._lock:
            incident_id = f"INC-{cls._next_incident_id:04d}"
            cls._next_incident_id += 1
            now = datetime.now(timezone.utc)
            incident = Incident(
                incident_id=incident_id,
                title=title,
                severity=severity,
                status=IncidentStatus.OPEN,
                description=description,
                affected_services=affected_services or [],
                owner=owner,
                tags=tags or [],
                created_at=now,
                updated_at=now,
                detected_at=now,
            )
            cls._incidents[incident_id] = incident
            cls._add_event(
                incident_id=incident_id,
                phase=IncidentPhase.DETECTION,
                actor="system",
                action="Incident created",
                details={"title": title, "severity": severity.value},
            )
            return incident

    @classmethod
    def add_event(
        cls,
        incident_id: str,
        phase: IncidentPhase,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
    ) -> Optional[TimelineEvent]:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            if not incident:
                return None
            event = TimelineEvent(
                event_id=f"EVT-{cls._next_event_id:04d}",
                incident_id=incident_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc),
                actor=actor,
                action=action,
                details=details or {},
                duration_ms=duration_ms,
            )
            incident.timeline.append(event)
            incident.updated_at = event.timestamp
            if phase == IncidentPhase.RESOLUTION:
                incident.status = IncidentStatus.RESOLVED
                incident.resolved_at = event.timestamp
            elif incident.status == IncidentStatus.OPEN:
                incident.status = IncidentStatus.INVESTIGATING
            cls._next_event_id += 1
            return event

    @classmethod
    def update_status(cls, incident_id: str, status: IncidentStatus) -> Optional[Incident]:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            if not incident:
                return None
            incident.status = status
            incident.updated_at = datetime.now(timezone.utc)
            return incident

    @classmethod
    def resolve_incident(cls, incident_id: str, root_cause: str = "") -> Optional[Incident]:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            if not incident:
                return None
            incident.status = IncidentStatus.RESOLVED
            incident.resolved_at = datetime.now(timezone.utc)
            incident.root_cause = root_cause
            incident.updated_at = incident.resolved_at
            cls.add_event(
                incident_id=incident_id,
                phase=IncidentPhase.RESOLUTION,
                actor="system",
                action="Incident resolved",
                details={"root_cause": root_cause},
            )
            return incident

    @classmethod
    def get_incident(cls, incident_id: str) -> Optional[Incident]:
        with cls._lock:
            return cls._incidents.get(incident_id)

    @classmethod
    def list_incidents(
        cls,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None,
        limit: int = 100,
    ) -> List[Incident]:
        with cls._lock:
            results = list(cls._incidents.values())
        if status:
            results = [i for i in results if i.status == status]
        if severity:
            results = [i for i in results if i.severity == severity]
        return sorted(results, key=lambda i: i.created_at, reverse=True)[:limit]

    @classmethod
    def get_timeline_events(cls, incident_id: str) -> List[TimelineEvent]:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            return list(incident.timeline) if incident else []

    @classmethod
    def get_mttr(cls) -> Dict[str, Any]:
        with cls._lock:
            resolved = [
                i for i in cls._incidents.values()
                if i.resolved_at and i.detected_at
            ]
        if not resolved:
            return {"mttr_seconds": 0.0, "count": 0}
        durations = [(i.resolved_at - i.detected_at).total_seconds() for i in resolved]
        durations.sort()
        n = len(durations)
        p50 = durations[n // 2]
        p95 = durations[int(n * 0.95)] if n > 1 else durations[0]
        p99 = durations[int(n * 0.99)] if n > 1 else durations[0]
        return {
            "mttr_seconds": sum(durations) / n,
            "p50_seconds": p50,
            "p95_seconds": p95,
            "p99_seconds": p99,
            "count": n,
        }

    @classmethod
    def _add_event(
        cls,
        incident_id: str,
        phase: IncidentPhase,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
    ) -> TimelineEvent:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            if not incident:
                raise ValueError(f"Incident {incident_id} not found")
            event = TimelineEvent(
                event_id=f"EVT-{cls._next_event_id:04d}",
                incident_id=incident_id,
                phase=phase,
                timestamp=datetime.now(timezone.utc),
                actor=actor,
                action=action,
                details=details or {},
                duration_ms=duration_ms,
            )
            incident.timeline.append(event)
            incident.updated_at = event.timestamp
            cls._next_event_id += 1
            return event

    @classmethod
    def export_timeline(cls, incident_id: str) -> Dict[str, Any]:
        with cls._lock:
            incident = cls._incidents.get(incident_id)
            if not incident:
                return {}
            events = [
                {
                    "event_id": e.event_id,
                    "phase": e.phase.value,
                    "timestamp": e.timestamp.isoformat(),
                    "actor": e.actor,
                    "action": e.action,
                    "details": e.details,
                    "duration_ms": e.duration_ms,
                }
                for e in incident.timeline
            ]
            return {
                "incident_id": incident.incident_id,
                "title": incident.title,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "created_at": incident.created_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "owner": incident.owner,
                "affected_services": incident.affected_services,
                "root_cause": incident.root_cause,
                "events": events,
            }
