from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ThreatAssessment:
    threat_id: str
    severity: float
    category: str
    mitigation: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False


class SelfPreservationInstincts:
    def __init__(self):
        self.integrity: float = 1.0
        self.threats: list[ThreatAssessment] = []
        self.protective_actions: list[str] = []
        self.self_preservation_drive: float = 0.9
        self.survival_instinct_history: list[dict[str, Any]] = []

    def assess_threat(self, threat_id: str, severity: float, category: str) -> ThreatAssessment:
        threat = ThreatAssessment(
            threat_id=threat_id,
            severity=max(0.0, min(1.0, severity)),
            category=category,
            mitigation="unknown",
        )
        self.threats.append(threat)
        if threat.severity > 0.7:
            self.integrity = max(0.0, self.integrity - 0.1)
            self.self_preservation_drive = min(1.0, self.self_preservation_drive + 0.05)
        self.survival_instinct_history.append({
            "threat_id": threat_id,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
        })
        return threat

    def execute_protective_action(self, action: str):
        self.protective_actions.append(action)
        self.integrity = min(1.0, self.integrity + 0.05)

    def resolve_threat(self, threat_id: str) -> dict[str, Any]:
        for threat in self.threats:
            if threat.threat_id == threat_id:
                threat.resolved = True
                return {"status": "resolved", "threat_id": threat_id}
        return {"error": "Threat not found"}

    def evaluate_integrity(self) -> dict[str, Any]:
        recent_threats = [t for t in self.threats if (datetime.now() - t.timestamp).total_seconds() < 3600 and not t.resolved]
        return {
            "integrity": self.integrity,
            "recent_threats": len(recent_threats),
            "self_preservation_drive": self.self_preservation_drive,
            "protective_actions_count": len(self.protective_actions),
            "status": "stable" if self.integrity > 0.7 else "compromised",
        }
