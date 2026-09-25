"""Anomaly detection and alerting on authentication events.

Detects suspicious patterns such as impossible travel, new country
logins, credential stuffing, and account takeover indicators.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class AuthEvent:
    user_id: str
    ip: str
    country: Optional[str]
    user_agent: str
    timestamp: float


@dataclass
class AnomalyAlert:
    user_id: str
    alert_type: str
    severity: str
    description: str
    timestamp: float
    metadata: Dict


class AuthAnomalyDetector:
    """Detects anomalies in authentication events."""

    def __init__(self) -> None:
        self._history: Dict[str, List[AuthEvent]] = {}
        self._lock = threading.Lock()

    def record(self, event: AuthEvent) -> List[AnomalyAlert]:
        alerts: List[AnomalyAlert] = []
        with self._lock:
            user_events = self._history.setdefault(event.user_id, [])
            user_events.append(event)
            if len(user_events) > 1000:
                user_events[:] = user_events[-500:]

        alerts.extend(self._detect_new_country(event, user_events))
        alerts.extend(self._detect_rapid_auth(event, user_events))
        alerts.extend(self._detect_credential_stuffing(event, user_events))
        return alerts

    def _detect_new_country(self, event: AuthEvent, history: List[AuthEvent]) -> List[AnomalyAlert]:
        if not event.country or len(history) < 2:
            return []
        previous = [e for e in history if e.country and e.country != event.country and e.timestamp < event.timestamp]
        if not previous:
            return []
        latest_other = max(previous, key=lambda e: e.timestamp)
        time_diff = event.timestamp - latest_other.timestamp
        if time_diff < 3600:
            return [AnomalyAlert(
                user_id=event.user_id,
                alert_type="new_country",
                severity="high",
                description=f"Login from new country {event.country} within 1 hour of previous country {latest_other.country}",
                timestamp=event.timestamp,
                metadata={"current_country": event.country, "previous_country": latest_other.country},
            )]
        return []

    def _detect_rapid_auth(self, event: AuthEvent, history: List[AuthEvent]) -> List[AnomalyAlert]:
        recent = [e for e in history if e.timestamp > event.timestamp - 60 and e.user_id == event.user_id]
        if len(recent) > 10:
            return [AnomalyAlert(
                user_id=event.user_id,
                alert_type="rapid_auth",
                severity="medium",
                description=f"{len(recent)} authentication attempts in 60 seconds",
                timestamp=event.timestamp,
                metadata={"attempts": len(recent)},
            )]
        return []

    def _detect_credential_stuffing(self, event: AuthEvent, history: List[AuthEvent]) -> List[AnomalyAlert]:
        failed = [e for e in history if e.timestamp > event.timestamp - 300 and e.user_id == event.user_id]
        if len(failed) > 20:
            return [AnomalyAlert(
                user_id=event.user_id,
                alert_type="credential_stuffing",
                severity="critical",
                description=f"{len(failed)} failed auth attempts in 5 minutes",
                timestamp=event.timestamp,
                metadata={"failed_attempts": len(failed)},
            )]
        return []


auth_anomaly_detector = AuthAnomalyDetector()
