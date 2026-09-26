"""API abuse and anomaly detection with behavioral profiling."""
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AbuseAlert:
    alert_id: str
    user_id: str
    severity: AlertSeverity
    description: str
    timestamp: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    is_resolved: bool = False


class AbuseDetector:
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._alerts: List[AbuseAlert] = []
        self._profiles: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "ips": set(), "endpoints": set(), "hours": [],
            "request_count": 0, "error_count": 0, "baseline_rph": 0.0,
        })
        self._lock = __import__('threading').Lock()
        self._rapid_threshold = 50
        self._rapid_window = 60.0
        self._bruteforce_threshold = 10
        self._bruteforce_window = 300.0

    def record_event(self, user_id: str, ip: str, endpoint: str, status_code: int, user_agent: str = "") -> List[AbuseAlert]:
        alerts = []
        now = time.time()
        event = {"user_id": user_id, "ip": ip, "endpoint": endpoint, "status_code": status_code, "timestamp": now}
        with self._lock:
            self._events.append(event)
            if len(self._events) > 10000:
                self._events = self._events[-5000:]

            profile = self._profiles[user_id]
            profile["ips"].add(ip)
            profile["endpoints"].add(endpoint)
            profile["hours"].append(time.localtime(now).tm_hour)
            profile["request_count"] += 1
            if status_code >= 400:
                profile["error_count"] += 1

            recent = [e for e in self._events if e["user_id"] == user_id and e["timestamp"] > now - self._rapid_window]
            if len(recent) >= self._rapid_threshold:
                alert = AbuseAlert(
                    alert_id=hashlib.sha256(f"{user_id}:{now}:rapid".encode()).hexdigest()[:16],
                    user_id=user_id, severity=AlertSeverity.HIGH,
                    description=f"Rapid requests: {len(recent)} in {self._rapid_window}s",
                    timestamp=now, evidence={"count": len(recent), "window": self._rapid_window},
                )
                alerts.append(alert)

            failed = [e for e in self._events if e["user_id"] == user_id and e["status_code"] == 401 and e["timestamp"] > now - self._bruteforce_window]
            if len(failed) >= self._bruteforce_threshold:
                alert = AbuseAlert(
                    alert_id=hashlib.sha256(f"{user_id}:{now}:bruteforce".encode()).hexdigest()[:16],
                    user_id=user_id, severity=AlertSeverity.CRITICAL,
                    description=f"Credential stuffing: {len(failed)} failed logins in {self._bruteforce_window}s",
                    timestamp=now, evidence={"failed_attempts": len(failed)},
                )
                alerts.append(alert)

            self._alerts.extend(alerts)
            if len(self._alerts) > 5000:
                self._alerts = self._alerts[-2500:]

        for alert in alerts:
            logger.warning("Abuse alert: %s", alert.description)
        return alerts

    def get_alerts(self, min_severity: AlertSeverity = AlertSeverity.MEDIUM) -> List[Dict[str, Any]]:
        with self._lock:
            return [a.__dict__ for a in self._alerts if not a.is_resolved and a.severity.value in (
                AlertSeverity.MEDIUM.value, AlertSeverity.HIGH.value, AlertSeverity.CRITICAL.value
            )][-100:]

    def resolve_alert(self, alert_id: str) -> bool:
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.is_resolved = True
                    return True
        return False

    def get_user_behavior_report(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(user_id, {})
            return {
                "user_id": user_id,
                "request_count": profile.get("request_count", 0),
                "error_count": profile.get("error_count", 0),
                "typical_ips": len(profile.get("ips", set())),
                "typical_endpoints": len(profile.get("endpoints", set())),
            }


abuse_detector = AbuseDetector()
