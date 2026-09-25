"""On-call escalation policy with schedule management, rotation, and automated escalation."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class EscalationLevel(str, Enum):
    L1 = "l1"
    L2 = "l2"
    L3 = "l3"
    L4 = "l4"


class EscalationAction(str, Enum):
    NOTIFY = "notify"
    PAGE = "page"
    CALL = "call"
    SMS = "sms"
    EMAIL = "email"
    SLACK = "slack"


@dataclass
class OnCallPerson:
    person_id: str
    name: str
    email: str
    phone: Optional[str] = None
    slack_handle: Optional[str] = None
    timezone: str = "UTC"
    escalation_level: EscalationLevel = EscalationLevel.L1
    notification_channels: List[EscalationAction] = field(default_factory=list)


@dataclass
class EscalationRule:
    rule_id: str
    name: str
    incident_severity: IncidentSeverity  # type: ignore[name-defined]
    max_response_minutes: int
    levels: List[EscalationLevel] = field(default_factory=lambda: [EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3])
    enabled: bool = True


@dataclass
class RotationSchedule:
    rotation_id: str
    name: str
    members: List[str]
    start_date: datetime
    rotation_days: int = 7
    handoff_hour: int = 9
    timezone: str = "UTC"


@dataclass
class EscalationEvent:
    event_id: str
    incident_id: str
    escalation_level: EscalationLevel
    action: EscalationAction
    triggered_at: datetime
    target_person_id: Optional[str]
    status: str = "pending"
    response_deadline: Optional[datetime] = None


class IncidentSeverity:
    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class OnCallEscalationPolicy:
    _persons: Dict[str, OnCallPerson] = {}
    _rules: Dict[str, EscalationRule] = {}
    _rotations: Dict[str, RotationSchedule] = {}
    _events: List[EscalationEvent] = []
    _current_rotation: Dict[str, str] = {}
    _lock = threading.RLock()
    _next_event_id = 1

    @classmethod
    def register_person(cls, person: OnCallPerson) -> None:
        with cls._lock:
            cls._persons[person.person_id] = person

    @classmethod
    def unregister_person(cls, person_id: str) -> None:
        with cls._lock:
            cls._persons.pop(person_id, None)

    @classmethod
    def register_rule(cls, rule: EscalationRule) -> None:
        with cls._lock:
            cls._rules[rule.rule_id] = rule

    @classmethod
    def register_rotation(cls, rotation: RotationSchedule) -> None:
        with cls._lock:
            cls._rotations[rotation.rotation_id] = rotation

    @classmethod
    def get_current_on_call(cls, rotation_id: str) -> Optional[OnCallPerson]:
        with cls._lock:
            rotation = cls._rotations.get(rotation_id)
            if not rotation:
                return None
            member_id = cls._current_rotation.get(rotation_id)
            if not member_id:
                member_id = cls._compute_current_member(rotation)
                cls._current_rotation[rotation_id] = member_id
            return cls._persons.get(member_id)

    @classmethod
    def get_escalation_chain(cls, incident_severity: str) -> List[EscalationLevel]:
        with cls._lock:
            matching = [
                r for r in cls._rules.values()
                if r.incident_severity == incident_severity and r.enabled
            ]
            if matching:
                return matching[0].levels
            return [EscalationLevel.L1, EscalationLevel.L2, EscalationLevel.L3]

    @classmethod
    def escalate(
        cls,
        incident_id: str,
        incident_severity: str,
        incident_title: str,
        notify_fn: Optional[Callable[[OnCallPerson, EscalationAction, str], bool]] = None,
    ) -> List[EscalationEvent]:
        with cls._lock:
            chain = cls.get_escalation_chain(incident_severity)
            events: List[EscalationEvent] = []
            for level in chain:
                person = cls._find_person_at_level(level)
                if not person:
                    continue
                action = cls._select_action(level, incident_severity)
                deadline = datetime.now(timezone.utc) + timedelta(minutes=cls._get_response_time(level))
                event = EscalationEvent(
                    event_id=f"EVT-{cls._next_event_id:04d}",
                    incident_id=incident_id,
                    escalation_level=level,
                    action=action,
                    triggered_at=datetime.now(timezone.utc),
                    target_person_id=person.person_id,
                    status="pending",
                    response_deadline=deadline,
                )
                cls._events.append(event)
                events.append(event)
                cls._next_event_id += 1
                if notify_fn:
                    try:
                        success = notify_fn(person, action, f"Escalation for {incident_id}: {incident_title}")
                        event.status = "sent" if success else "failed"
                    except Exception:
                        event.status = "failed"
                if not person:
                    continue
                break
            return events

    @classmethod
    def acknowledge_escalation(cls, event_id: str) -> bool:
        with cls._lock:
            for event in cls._events:
                if event.event_id == event_id:
                    event.status = "acknowledged"
                    return True
            return False

    @classmethod
    def get_pending_escalations(cls) -> List[EscalationEvent]:
        with cls._lock:
            now = datetime.now(timezone.utc)
            return [
                e for e in cls._events
                if e.status == "pending"
                and e.response_deadline
                and now > e.response_deadline
            ]

    @classmethod
    def _compute_current_member(cls, rotation: RotationSchedule) -> str:
        if not rotation.members:
            return ""
        now = datetime.now(timezone.utc)
        elapsed = now - rotation.start_date
        elapsed_days = elapsed.days
        idx = (elapsed_days // rotation.rotation_days) % len(rotation.members)
        return rotation.members[idx]

    @classmethod
    def _find_person_at_level(cls, level: EscalationLevel) -> Optional[OnCallPerson]:
        with cls._lock:
            for person in cls._persons.values():
                if person.escalation_level == level:
                    return person
        return None

    @classmethod
    def _select_action(cls, level: EscalationLevel, severity: str) -> EscalationAction:
        if severity in ("p1_critical", "p2_high"):
            return EscalationAction.PAGE
        if level == EscalationLevel.L1:
            return EscalationAction.SLACK
        return EscalationAction.EMAIL

    @classmethod
    def _get_response_time(cls, level: EscalationLevel) -> int:
        times = {
            EscalationLevel.L1: 15,
            EscalationLevel.L2: 10,
            EscalationLevel.L3: 5,
            EscalationLevel.L4: 2,
        }
        return times.get(level, 15)

    @classmethod
    def get_policy_summary(cls) -> Dict[str, Any]:
        with cls._lock:
            return {
                "persons": list(cls._persons.keys()),
                "rules": len(cls._rules),
                "rotations": len(cls._rotations),
                "pending_escalations": len(cls.get_pending_escalations()),
            }


oncall = OnCallEscalationPolicy()
