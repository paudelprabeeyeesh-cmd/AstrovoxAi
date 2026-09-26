"""Threat detection for security excellence."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ThreatSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatAlert:
    alert_id: str
    threat_type: str
    severity: ThreatSeverity
    source: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ThreatDetector:
    def __init__(self) -> None:
        self._alerts: List[ThreatAlert] = []

    def detect(self, event: Dict[str, Any]) -> Optional[ThreatAlert]:
        threat_type = event.get("type", "unknown")
        alert = ThreatAlert(
            alert_id=uuid.uuid4().hex,
            threat_type=threat_type,
            severity=ThreatSeverity.MEDIUM,
            source=event.get("source", "unknown"),
            description=event.get("description", ""),
        )
        self._alerts.append(alert)
        return alert

    def get_alerts(self, severity: Optional[ThreatSeverity] = None) -> List[ThreatAlert]:
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return list(self._alerts)


threat_detector = ThreatDetector()
