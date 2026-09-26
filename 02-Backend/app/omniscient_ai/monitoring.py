"""Omnipresent Monitoring - Monitors everything everywhere all at once."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class MonitorEvent:
    event_id: str
    source: str
    event_type: str
    severity: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class OmnipresentMonitor:
    """Monitors all systems, all users, all events simultaneously."""

    def __init__(self):
        self._events: List[MonitorEvent] = []
        self._monitors: Dict[str, Dict[str, Any]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._health_checks: Dict[str, float] = {}

    def register_monitor(self, name: str, config: Dict[str, Any]) -> str:
        monitor_id = str(uuid.uuid4())
        self._monitors[monitor_id] = {
            "name": name,
            "config": config,
            "active": True,
            "created_at": time.time(),
        }
        return monitor_id

    def record_event(self, source: str, event_type: str, severity: str = "info", data: Dict[str, Any] = None) -> MonitorEvent:
        event = MonitorEvent(
            event_id=str(uuid.uuid4()),
            source=source,
            event_type=event_type,
            severity=severity,
            data=data or {},
        )
        self._events.append(event)
        if severity in ("error", "critical"):
            self._alerts.append({
                "event_id": event.event_id,
                "severity": severity,
                "source": source,
                "timestamp": event.timestamp,
            })
        return event

    def get_health_status(self) -> Dict[str, Any]:
        return {
            "monitors": len(self._monitors),
            "active_monitors": sum(1 for m in self._monitors.values() if m.get("active")),
            "events": len(self._events),
            "alerts": len(self._alerts),
            "health_scores": dict(self._health_checks),
        }

    def get_alerts(self, severity: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        alerts = self._alerts
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]
        return alerts[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_events": len(self._events),
            "alerts": len(self._alerts),
            "monitors": len(self._monitors),
            "health_checks": len(self._health_checks),
        }
