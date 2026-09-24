"""Real-time security monitoring with event collection and alerting."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np


@dataclass
class SecurityEvent:
    timestamp: float
    source: str
    event_type: str
    message: str
    severity: str
    metadata: dict = field(default_factory=dict)


@dataclass
class AlertRule:
    name: str
    event_type: str
    threshold: float
    window_seconds: float
    severity: str
    condition: str = "count"


@dataclass
class Alert:
    rule: AlertRule
    triggered_at: float
    event_count: int
    value: float
    message: str


class SecurityMonitor:
    def __init__(self) -> None:
        self._events: list[SecurityEvent] = []
        self._rules: list[AlertRule] = []
        self._alerts: list[Alert] = []
        self._handlers: list[Callable[[Alert], None]] = []

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def on_alert(self, handler: Callable[[Alert], None]) -> None:
        self._handlers.append(handler)

    def log_event(self, source: str, event_type: str, message: str, severity: str = "info", metadata: dict | None = None) -> SecurityEvent:
        event = SecurityEvent(timestamp=time.time(), source=source, event_type=event_type, message=message, severity=severity, metadata=metadata or {})
        self._events.append(event)
        self._evaluate(event)
        return event

    def _evaluate(self, event: SecurityEvent) -> None:
        now = event.timestamp
        for rule in self._rules:
            if rule.event_type != event.event_type:
                continue
            window_start = now - rule.window_seconds
            matching = [e for e in self._events if e.event_type == rule.event_type and e.timestamp >= window_start]
            value = float(len(matching))
            triggered = value >= rule.threshold
            if triggered:
                alert = Alert(rule=rule, triggered_at=now, event_count=len(matching), value=value, message=f"{rule.name} triggered: {value:.0f} events in {rule.window_seconds}s")
                self._alerts.append(alert)
                for handler in self._handlers:
                    handler(alert)

    def get_events(self, event_type: str | None = None, since: float | None = None) -> list[SecurityEvent]:
        events = self._events
        if event_type is not None:
            events = [e for e in events if e.event_type == event_type]
        if since is not None:
            events = [e for e in events if e.timestamp >= since]
        return events

    def get_alerts(self, since: float | None = None) -> list[Alert]:
        alerts = self._alerts
        if since is not None:
            alerts = [a for a in alerts if a.triggered_at >= since]
        return alerts

    def compute_metrics(self) -> dict:
        if not self._events:
            return {"event_count": 0, "alert_count": 0, "avg_events_per_minute": 0.0}
        timestamps = np.array([e.timestamp for e in self._events], dtype=np.float64)
        span = float(np.max(timestamps) - np.min(timestamps))
        rate = len(self._events) / (span / 60.0) if span > 0 else 0.0
        return {
            "event_count": len(self._events),
            "alert_count": len(self._alerts),
            "avg_events_per_minute": float(rate),
            "event_types": len(set(e.event_type for e in self._events)),
        }
