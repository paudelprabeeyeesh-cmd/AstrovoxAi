"""Intrusion detection and anomaly monitoring."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    event_id: str
    source_ip: str
    action: str
    severity: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class IntrusionAlert:
    alert_id: str
    source_ip: str
    rule_id: str
    severity: str
    description: str
    score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class IntrusionDetector:
    def __init__(self) -> None:
        self._events: List[SecurityEvent] = []
        self._alerts: List[IntrusionAlert] = []
        self._ip_attempts: Dict[str, List[float]] = defaultdict(list)
        self._rules: Dict[str, Callable[..., Any]] = {}

    def add_rule(self, rule_id: str, rule_fn: Callable[..., Any]) -> None:
        self._rules[rule_id] = rule_fn

    def record_event(self, event: SecurityEvent) -> None:
        self._events.append(event)
        self._ip_attempts[event.source_ip].append(event.timestamp.timestamp())
        for rule_id, rule_fn in self._rules.items():
            try:
                if rule_fn(event, self._events):
                    self._alerts.append(IntrusionAlert(
                        alert_id=str(__import__("uuid").uuid4()),
                        source_ip=event.source_ip,
                        rule_id=rule_id,
                        severity=event.severity,
                        description=f"Rule {rule_id} triggered",
                        score=1.0,
                    ))
            except Exception:
                logger.exception("Rule evaluation failed for %s", rule_id)

    def detect_brute_force(self, window_seconds: float = 60.0, threshold: int = 10) -> List[IntrusionAlert]:
        alerts = []
        cutoff = time.time() - window_seconds
        for ip, attempts in self._ip_attempts.items():
            recent = [t for t in attempts if t > cutoff]
            if len(recent) >= threshold:
                alerts.append(IntrusionAlert(
                    alert_id=str(__import__("uuid").uuid4()),
                    source_ip=ip,
                    rule_id="brute_force",
                    severity="high",
                    description=f"Brute force detected from {ip}: {len(recent)} attempts in {window_seconds}s",
                    score=min(len(recent) / threshold, 1.0),
                ))
        return alerts

    def recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "alert_id": a.alert_id,
                "source_ip": a.source_ip,
                "rule_id": a.rule_id,
                "severity": a.severity,
                "description": a.description,
                "score": a.score,
                "timestamp": a.timestamp.isoformat(),
            }
            for a in self._alerts[-limit:]
        ]


intrusion_detector = IntrusionDetector()
