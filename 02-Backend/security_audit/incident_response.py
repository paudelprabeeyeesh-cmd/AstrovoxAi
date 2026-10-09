"""Incident detection and response automation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Sequence



@dataclass
class Incident:
    id: str
    title: str
    severity: str
    status: str
    detected_at: float
    updated_at: float
    indicators: list[str]
    affected_assets: list[str]
    response_actions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PlaybookStep:
    action: str
    params: dict = field(default_factory=dict)
    auto: bool = True


@dataclass
class Playbook:
    name: str
    incident_type: str
    steps: list[PlaybookStep]


_INCIDENT_COUNTER = 0


class IncidentResponseSystem:
    DEFAULT_PLAYBOOKS = [
        Playbook("malware_outbreak", "malware", [
            PlaybookStep("isolate_asset", {"scope": "affected"}),
            PlaybookStep("collect_evidence"),
            PlaybookStep("scan_antivirus"),
            PlaybookStep("remediate", {"method": "automatic"}),
            PlaybookStep("notify_team"),
        ]),
        Playbook("data_breach", "data_breach", [
            PlaybookStep("contain_breach", {"scope": "all"}),
            PlaybookStep("assess_exposure"),
            PlaybookStep("notify_affected", {"delay_hours": 72}),
            PlaybookStep("reset_credentials", {"scope": "affected"}),
        ]),
        Playbook("ddos_attack", "dos", [
            PlaybookStep("enable_rate_limiting"),
            PlaybookStep("blackhole_routes", {"duration_minutes": 30}),
            PlaybookStep("scale_resources"),
            PlaybookStep("notify_upstream"),
        ]),
        Playbook("unauthorized_access", "access_control", [
            PlaybookStep("revoke_sessions"),
            PlaybookStep("disable_accounts", {"scope": "compromised"}),
            PlaybookStep("audit_logs"),
            PlaybookStep("notify_security_team"),
        ]),
    ]

    def __init__(self, playbooks: Sequence[Playbook] | None = None) -> None:
        self.playbooks = list(playbooks or self.DEFAULT_PLAYBOOKS)
        self._incidents: dict[str, Incident] = {}

    def _next_id(self) -> str:
        global _INCIDENT_COUNTER
        _INCIDENT_COUNTER += 1
        return f"INC-{_INCIDENT_COUNTER:06d}"

    def detect(self, indicators: Sequence[str], affected_assets: Sequence[str], severity: str = "medium") -> Incident:
        incident = Incident(
            id=self._next_id(),
            title=f"Security incident detected",
            severity=severity,
            status="open",
            detected_at=time.time(),
            updated_at=time.time(),
            indicators=list(indicators),
            affected_assets=list(affected_assets),
        )
        self._incidents[incident.id] = incident
        return incident

    def classify(self, incident: Incident) -> str:
        indicators_text = " ".join(incident.indicators).lower()
        if any(k in indicators_text for k in ["malware", "ransomware", "virus", "trojan"]):
            return "malware"
        if any(k in indicators_text for k in ["leak", "exfiltrat", "breach", "unauthorized access"]):
            return "data_breach"
        if any(k in indicators_text for k in ["ddos", "flood", "amplification"]):
            return "dos"
        if any(k in indicators_text for k in ["login", "credential", "access", "privilege"]):
            return "access_control"
        return "generic"

    def respond(self, incident: Incident) -> list[str]:
        incident_type = self.classify(incident)
        playbook = next((p for p in self.playbooks if p.incident_type == incident_type), None)
        if playbook is None:
            incident.response_actions.append("manual_investigation")
            incident.status = "investigating"
            return incident.response_actions
        for step in playbook.steps:
            incident.response_actions.append(step.action)
            if step.auto:
                incident.response_actions.append(f"auto:{step.action}")
        incident.status = "contained"
        incident.updated_at = time.time()
        return incident.response_actions

    def get_incident(self, incident_id: str) -> Incident | None:
        return self._incidents.get(incident_id)

    def compute_severity_score(self, incident: Incident) -> float:
        severity_weights = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
        base = severity_weights.get(incident.severity, 0.5)
        asset_factor = min(len(incident.affected_assets) * 0.1, 1.0)
        indicator_factor = min(len(incident.indicators) * 0.05, 1.0)
        return min(1.0, base + asset_factor * 0.3 + indicator_factor * 0.2)

    def list_incidents(self) -> list[Incident]:
        return list(self._incidents.values())
