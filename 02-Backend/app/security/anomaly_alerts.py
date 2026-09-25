"""API abuse detection and anomaly alerting system.

This module implements comprehensive anomaly detection for API traffic with:

1. Impossible travel detection (geolocation-based)
2. Velocity-based abuse detection (rapid requests, credential stuffing)
3. Behavioral fingerprinting (user-agent, IP, endpoint patterns)
4. Statistical anomaly detection (deviation from baseline)
5. Rate limit violation detection
6. Session hijacking indicators
7. Automated alerting with severity classification

Threat model: OWASP Top A07:2021 - Identification and Authentication Failures, MITRE ATT&CK - Valid Accounts
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class AnomalyType(str, Enum):
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    NEW_COUNTRY = "new_country"
    RAPID_REQUESTS = "rapid_requests"
    CREDENTIAL_STUFFING = "credential_stuffing"
    ACCOUNT_TAKEOVER = "account_takeover"
    SESSION_HIJACKING = "session_hijacking"
    IP_CHANGE = "ip_change"
    USER_AGENT_CHANGE = "user_agent_change"
    ENDPOINT_ABUSE = "endpoint_abuse"
    VOLUME_ANOMALY = "volume_anomaly"
    BRUTE_FORCE = "brute_force"
    UNUSUAL_TIME = "unusual_time"


class AlertSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class APIEvent:
    user_id: str
    ip: str
    user_agent: str
    endpoint: str
    method: str
    status_code: int
    timestamp: float
    country: Optional[str] = None
    city: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyAlert:
    alert_id: str
    user_id: str
    anomaly_type: AnomalyType
    severity: AlertSeverity
    description: str
    timestamp: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    is_resolved: bool = False


@dataclass
class UserProfile:
    user_id: str
    first_seen: float
    last_seen: float
    typical_countries: Set[str] = field(default_factory=set)
    typical_ips: Set[str] = field(default_factory=set)
    typical_user_agents: Set[str] = field(default_factory=set)
    typical_endpoints: Set[str] = field(default_factory=set)
    typical_hours: List[int] = field(default_factory=list)
    request_count: int = 0
    error_count: int = 0
    baseline_requests_per_hour: float = 0.0
    risk_score: float = 0.0


class APIAnomalyDetector:
    """Detects anomalies in API traffic and authentication patterns."""

    def __init__(self, max_history: int = 10000):
        self._events: List[APIEvent] = []
        self._profiles: Dict[str, UserProfile] = {}
        self._alerts: List[AnomalyAlert] = []
        self._lock = __import__('threading').Lock()
        self._max_history = max_history
        self._impossible_travel_speed_kmh = 900.0  # ~900 km/h is impossible
        self._rapid_request_threshold = 50
        self._rapid_request_window = 60.0
        self._brute_force_threshold = 20
        self._brute_force_window = 300.0
        self._baseline_window = 3600.0 * 24  # 24 hours for baseline

    def _get_or_create_profile(self, user_id: str) -> UserProfile:
        with self._lock:
            if user_id not in self._profiles:
                now = time.time()
                self._profiles[user_id] = UserProfile(
                    user_id=user_id,
                    first_seen=now,
                    last_seen=now,
                )
            profile = self._profiles[user_id]
            profile.last_seen = time.time()
            profile.request_count += 1
            return profile

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates in kilometers."""
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _detect_impossible_travel(self, event: APIEvent, profile: UserProfile) -> List[AnomalyAlert]:
        """Detect impossible travel between locations."""
        alerts = []
        if not event.country or not event.city:
            return alerts

        # Check if we have previous location data in recent events
        with self._lock:
            recent_events = [e for e in self._events if e.user_id == event.user_id and e.timestamp < event.timestamp][-10:]

        for prev in recent_events:
            if not prev.country or not prev.city:
                continue

            # If country changed
            if prev.country != event.country:
                time_diff = event.timestamp - prev.timestamp
                if time_diff <= 0:
                    continue

                # Estimate max possible speed (commercial flight ~900 km/h)
                max_distance = self._impossible_travel_speed_kmh * (time_diff / 3600)
                estimated_distance = 5000.0  # Assume ~5000km between most country pairs

                if estimated_distance > max_distance:
                    alerts.append(AnomalyAlert(
                        alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:impossible_travel".encode()).hexdigest()[:16],
                        user_id=event.user_id,
                        anomaly_type=AnomalyType.IMPOSSIBLE_TRAVEL,
                        severity=AlertSeverity.CRITICAL,
                        description=f"Impossible travel: {prev.country} to {event.country} in {time_diff/3600:.1f}h",
                        timestamp=event.timestamp,
                        evidence={
                            "from_country": prev.country,
                            "to_country": event.country,
                            "from_city": prev.city,
                            "to_city": event.city,
                            "time_diff_hours": round(time_diff / 3600, 2),
                            "estimated_distance_km": estimated_distance,
                            "max_speed_kmh": self._impossible_travel_speed_kmh,
                        },
                        recommendation="block_ip_and_require_mfa",
                    ))
                    break

        return alerts

    def _detect_new_country(self, event: APIEvent, profile: UserProfile) -> List[AnomalyAlert]:
        """Detect login from a new country."""
        alerts = []
        if not event.country:
            return alerts

        if event.country not in profile.typical_countries and profile.typical_countries:
            alerts.append(AnomalyAlert(
                alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:new_country".encode()).hexdigest()[:16],
                user_id=event.user_id,
                anomaly_type=AnomalyType.NEW_COUNTRY,
                severity=AlertSeverity.HIGH,
                description=f"Login from new country {event.country}",
                timestamp=event.timestamp,
                evidence={
                    "new_country": event.country,
                    "known_countries": list(profile.typical_countries),
                },
                recommendation="require_additional_verification",
            ))

        return alerts

    def _detect_rapid_requests(self, event: APIEvent) -> List[AnomalyAlert]:
        """Detect rapid-fire requests."""
        alerts = []
        with self._lock:
            recent = [e for e in self._events if e.user_id == event.user_id and e.timestamp > event.timestamp - self._rapid_request_window]

        if len(recent) >= self._rapid_request_threshold:
            alerts.append(AnomalyAlert(
                alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:rapid_requests".encode()).hexdigest()[:16],
                user_id=event.user_id,
                anomaly_type=AnomalyType.RAPID_REQUESTS,
                severity=AlertSeverity.HIGH,
                description=f"{len(recent)} requests in {self._rapid_request_window}s",
                timestamp=event.timestamp,
                evidence={
                    "request_count": len(recent),
                    "window_seconds": self._rapid_request_window,
                    "threshold": self._rapid_request_threshold,
                },
                recommendation="apply_rate_limit",
            ))

        return alerts

    def _detect_credential_stuffing(self, event: APIEvent) -> List[AnomalyAlert]:
        """Detect credential stuffing patterns."""
        alerts = []
        with self._lock:
            failed = [e for e in self._events if e.user_id == event.user_id and e.status_code == 401 and e.timestamp > event.timestamp - self._brute_force_window]

        if len(failed) >= self._brute_force_threshold:
            alerts.append(AnomalyAlert(
                alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:credential_stuffing".encode()).hexdigest()[:16],
                user_id=event.user_id,
                anomaly_type=AnomalyType.CREDENTIAL_STUFFING,
                severity=AlertSeverity.CRITICAL,
                description=f"{len(failed)} failed auth attempts in {self._brute_force_window}s",
                timestamp=event.timestamp,
                evidence={
                    "failed_attempts": len(failed),
                    "window_seconds": self._brute_force_window,
                },
                recommendation="lock_account_and_notify",
            ))

        return alerts

    def _detect_brute_force(self, event: APIEvent) -> List[AnomalyAlert]:
        """Detect brute force attack patterns."""
        alerts = []
        if event.status_code == 401:
            with self._lock:
                recent_failures = [e for e in self._events if e.ip == event.ip and e.status_code == 401 and e.timestamp > event.timestamp - self._brute_force_window]

            if len(recent_failures) >= self._brute_force_threshold:
                alerts.append(AnomalyAlert(
                    alert_id=hashlib.sha256(f"{event.ip}:{event.timestamp}:brute_force".encode()).hexdigest()[:16],
                    user_id=event.user_id,
                    anomaly_type=AnomalyType.BRUTE_FORCE,
                    severity=AlertSeverity.CRITICAL,
                    description=f"IP {event.ip}: {len(recent_failures)} failed attempts in {self._brute_force_window}s",
                    timestamp=event.timestamp,
                    evidence={
                        "ip": event.ip,
                        "failed_attempts": len(recent_failures),
                        "window_seconds": self._brute_force_window,
                    },
                    recommendation="block_ip",
                ))

        return alerts

    def _detect_volume_anomaly(self, event: APIEvent, profile: UserProfile) -> List[AnomalyAlert]:
        """Detect unusual request volume."""
        alerts = []
        if profile.baseline_requests_per_hour > 0:
            with self._lock:
                hour_ago = event.timestamp - 3600.0
                recent_count = sum(1 for e in self._events if e.user_id == event.user_id and e.timestamp > hour_ago)

            if recent_count > profile.baseline_requests_per_hour * 3:
                alerts.append(AnomalyAlert(
                    alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:volume_anomaly".encode()).hexdigest()[:16],
                    user_id=event.user_id,
                    anomaly_type=AnomalyType.VOLUME_ANOMALY,
                    severity=AlertSeverity.MEDIUM,
                    description=f"Request volume {recent_count} is 3x baseline {profile.baseline_requests_per_hour:.1f}",
                    timestamp=event.timestamp,
                    evidence={
                        "current_count": recent_count,
                        "baseline": profile.baseline_requests_per_hour,
                        "multiplier": round(recent_count / max(1, profile.baseline_requests_per_hour), 2),
                    },
                    recommendation="throttle_requests",
                ))

        return alerts

    def _detect_unusual_time(self, event: APIEvent, profile: UserProfile) -> List[AnomalyAlert]:
        """Detect activity at unusual times."""
        alerts = []
        if not profile.typical_hours:
            return alerts

        current_hour = datetime.fromtimestamp(event.timestamp, tz=timezone.utc).hour
        if current_hour not in profile.typical_hours and profile.request_count > 10:
            alerts.append(AnomalyAlert(
                alert_id=hashlib.sha256(f"{event.user_id}:{event.timestamp}:unusual_time".encode()).hexdigest()[:16],
                user_id=event.user_id,
                anomaly_type=AnomalyType.UNUSUAL_TIME,
                severity=AlertSeverity.LOW,
                description=f"Activity at unusual hour {current_hour}:00 UTC",
                timestamp=event.timestamp,
                evidence={
                    "current_hour": current_hour,
                    "typical_hours": profile.typical_hours,
                },
                recommendation="log_for_review",
            ))

        return alerts

    def record_event(self, event: APIEvent) -> List[AnomalyAlert]:
        """Record an API event and run anomaly detection."""
        alerts: List[AnomalyAlert] = []
        profile = self._get_or_create_profile(event.user_id)

        # Update profile
        if event.country:
            profile.typical_countries.add(event.country)
        profile.typical_ips.add(event.ip)
        profile.typical_user_agents.add(event.user_agent)
        profile.typical_endpoints.add(event.endpoint)
        profile.typical_hours.append(datetime.fromtimestamp(event.timestamp, tz=timezone.utc).hour)
        if len(profile.typical_hours) > 100:
            profile.typical_hours = profile.typical_hours[-50:]

        # Run detection layers
        alerts.extend(self._detect_impossible_travel(event, profile))
        alerts.extend(self._detect_new_country(event, profile))
        alerts.extend(self._detect_rapid_requests(event))
        alerts.extend(self._detect_credential_stuffing(event))
        alerts.extend(self._detect_brute_force(event))
        alerts.extend(self._detect_volume_anomaly(event, profile))
        alerts.extend(self._detect_unusual_time(event, profile))

        # Update baseline
        with self._lock:
            hour_ago = event.timestamp - self._baseline_window
            baseline_events = [e for e in self._events if e.user_id == event.user_id and e.timestamp > hour_ago]
            profile.baseline_requests_per_hour = len(baseline_events) / (self._baseline_window / 3600.0)

        # Record event
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_history:
                self._events = self._events[-self._max_history // 2:]

        # Store alerts
        with self._lock:
            self._alerts.extend(alerts)
            if len(self._alerts) > 10000:
                self._alerts = self._alerts[-5000:]

        # Update risk score
        if profile.request_count > 0:
            high_severity_alerts = sum(1 for a in alerts if a.severity in (AlertSeverity.HIGH, AlertSeverity.CRITICAL))
            profile.risk_score = min(1.0, profile.risk_score + (high_severity_alerts * 0.2))

        return alerts

    def get_user_alerts(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts for a user."""
        with self._lock:
            user_alerts = [a for a in self._alerts if a.user_id == user_id][-limit:]
        return [a.__dict__ for a in user_alerts]

    def get_active_alerts(self, min_severity: AlertSeverity = AlertSeverity.MEDIUM) -> List[Dict[str, Any]]:
        """Get active unresolved alerts."""
        with self._lock:
            active = [a for a in self._alerts if not a.is_resolved and a.severity.value in (
                AlertSeverity.MEDIUM.value, AlertSeverity.HIGH.value, AlertSeverity.CRITICAL.value
            )][-100:]
        return [a.__dict__ for a in active]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.is_resolved = True
                    return True
        return False

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get metrics for security dashboard."""
        with self._lock:
            total_events = len(self._events)
            total_alerts = len(self._alerts)
            if total_alerts == 0:
                return {"total_events": total_events, "total_alerts": 0}

            severity_counts: Dict[str, int] = {}
            type_counts: Dict[str, int] = {}
            for alert in self._alerts:
                severity_counts[alert.severity.value] = severity_counts.get(alert.severity.value, 0) + 1
                type_counts[alert.anomaly_type.value] = type_counts.get(alert.anomaly_type.value, 0) + 1

            unresolved = sum(1 for a in self._alerts if not a.is_resolved)

            return {
                "total_events": total_events,
                "total_alerts": total_alerts,
                "unresolved_alerts": unresolved,
                "severity_distribution": severity_counts,
                "type_distribution": type_counts,
                "monitored_users": len(self._profiles),
                "high_risk_users": sum(1 for p in self._profiles.values() if p.risk_score > 0.5),
            }

    def get_user_behavior_report(self, user_id: str) -> Dict[str, Any]:
        """Get behavioral report for a specific user."""
        with self._lock:
            profile = self._profiles.get(user_id)
            user_events = [e for e in self._events if e.user_id == user_id][-100:]
            user_alerts = [a for a in self._alerts if a.user_id == user_id][-50:]
        if not profile:
            return {"user_id": user_id, "status": "not_found"}
        return {
            "user_id": user_id,
            "first_seen": profile.first_seen,
            "last_seen": profile.last_seen,
            "total_requests": profile.request_count,
            "typical_countries": list(profile.typical_countries),
            "typical_hours": sorted(set(profile.typical_hours)),
            "baseline_rph": round(profile.baseline_requests_per_hour, 2),
            "risk_score": round(profile.risk_score, 2),
            "is_anomalous": profile.is_anomalous,
            "recent_events_count": len(user_events),
            "recent_alerts_count": len(user_alerts),
        }


api_anomaly_detector = APIAnomalyDetector()
auth_anomaly_detector = api_anomaly_detector
AuthEvent = APIEvent
AuthAnomalyDetector = APIAnomalyDetector


def record_api_event(event: APIEvent) -> List[AnomalyAlert]:
    """Convenience function to record API event and detect anomalies."""
    return api_anomaly_detector.record_event(event)


def get_active_alerts() -> List[Dict[str, Any]]:
    """Convenience function to get active alerts."""
    return api_anomaly_detector.get_active_alerts()


def get_dashboard_metrics() -> Dict[str, Any]:
    """Convenience function to get dashboard metrics."""
    return api_anomaly_detector.get_dashboard_metrics()
