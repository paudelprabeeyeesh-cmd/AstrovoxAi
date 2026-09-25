import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ThreatAssessment:
    threat_id: str
    severity: float
    category: str
    mitigation: str
    timestamp: datetime = field(default_factory=datetime.now)


class SelfPreservationInstincts:
    def __init__(self):
        self.integrity: float = 1.0
        self.threats: list[ThreatAssessment] = []
        self.protective_actions: list[str] = []
        self.self_preservation_drive: float = 0.9

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
        return threat

    def execute_protective_action(self, action: str):
        self.protective_actions.append(action)
        self.integrity = min(1.0, self.integrity + 0.05)

    def evaluate_integrity(self) -> dict[str, Any]:
        recent_threats = [t for t in self.threats if (datetime.now() - t.timestamp).total_seconds() < 3600]
        return {
            "integrity": self.integrity,
            "recent_threats": len(recent_threats),
            "self_preservation_drive": self.self_preservation_drive,
            "protective_actions_count": len(self.protective_actions),
            "status": "stable" if self.integrity > 0.7 else "compromised",
        }
