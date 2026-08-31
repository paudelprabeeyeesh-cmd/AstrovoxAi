"""Security audit logging and enhanced rate limiting."""

import time
import hashlib
import hmac
import logging
import os
import json
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """A security audit event."""
    event_type: str
    user_id: str
    ip_address: str
    timestamp: float
    details: dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical


class AuditLogger:
    """Security audit logging system."""

    def __init__(self):
        self._events: list[AuditEvent] = []

    def log_authentication(self, user_id: str, ip_address: str, success: bool, method: str = "password"):
        """Log an authentication event."""
        event = AuditEvent(
            event_type="authentication",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=time.time(),
            details={"success": success, "method": method},
            severity="info" if success else "warning",
        )
        self._events.append(event)
        if not success:
            logger.warning(f"Failed authentication for user {user_id} from {ip_address}")

    def log_authorization(self, user_id: str, ip_address: str, resource: str, granted: bool):
        """Log an authorization check."""
        event = AuditEvent(
            event_type="authorization",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=time.time(),
            details={"resource": resource, "granted": granted},
            severity="warning" if not granted else "info",
        )
        self._events.append(event)

    def log_data_access(self, user_id: str, ip_address: str, resource: str, action: str):
        """Log data access."""
        event = AuditEvent(
            event_type="data_access",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=time.time(),
            details={"resource": resource, "action": action},
        )
        self._events.append(event)

    def log_security_event(self, user_id: str, ip_address: str, event_subtype: str, details: dict):
        """Log a generic security event."""
        event = AuditEvent(
            event_type=f"security_{event_subtype}",
            user_id=user_id,
            ip_address=ip_address,
            timestamp=time.time(),
            details=details,
            severity="warning",
        )
        self._events.append(event)
        logger.warning(f"Security event: {event_subtype} for user {user_id} from {ip_address}")

    def get_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        since: float = 0,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get audit events with filtering."""
        events = [e for e in self._events if e.timestamp >= since]

        if user_id:
            events = [e for e in events if e.user_id == user_id]
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_failed_logins(self, since: float = 86400) -> list[AuditEvent]:
        """Get failed login attempts."""
        return [
            e for e in self._events
            if e.event_type == "authentication"
            and not e.details.get("success", True)
            and e.timestamp >= since
        ]

    def get_suspicious_activity(self, since: float = 3600) -> list[AuditEvent]:
        """Get suspicious activity events."""
        return [
            e for e in self._events
            if e.severity in ("warning", "critical")
            and e.timestamp >= since
        ]

    def export_events(self, format: str = "json") -> str:
        """Export audit events."""
        events_data = [
            {
                "event_type": e.event_type,
                "user_id": e.user_id,
                "ip_address": e.ip_address,
                "timestamp": datetime.fromtimestamp(e.timestamp).isoformat(),
                "details": e.details,
                "severity": e.severity,
            }
            for e in self._events
        ]

        if format == "json":
            return json.dumps(events_data, indent=2)
        return ""


class RateLimiter:
    """Enhanced rate limiter with per-user and per-endpoint tracking."""

    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._limits: dict[str, tuple[int, int]] = {
            "default": (120, 60),
            "auth": (5, 60),
            "chat": (30, 60),
            "api": (60, 60),
        }

    def set_limit(self, endpoint: str, max_requests: int, window_seconds: int):
        """Set a rate limit for an endpoint."""
        self._limits[endpoint] = (max_requests, window_seconds)

    def is_allowed(self, identifier: str, endpoint: str = "default") -> tuple[bool, dict]:
        """Check if a request is allowed."""
        now = time.time()
        key = f"{identifier}:{endpoint}"

        if endpoint in self._limits:
            max_requests, window = self._limits[endpoint]
        else:
            max_requests, window = self._limits["default"]

        cutoff = now - window
        self._requests[key] = [t for t in self._requests[key] if t >= cutoff]

        current_count = len(self._requests[key])
        allowed = current_count < max_requests

        if allowed:
            self._requests[key].append(now)

        return allowed, {
            "limit": max_requests,
            "remaining": max(0, max_requests - current_count - (1 if allowed else 0)),
            "reset": int(now + window),
            "window": window,
        }

    def get_remaining(self, identifier: str, endpoint: str = "default") -> int:
        """Get remaining requests for an identifier."""
        key = f"{identifier}:{endpoint}"
        if endpoint in self._limits:
            max_requests, window = self._limits[endpoint]
        else:
            max_requests, window = self._limits["default"]

        cutoff = time.time() - window
        self._requests[key] = [t for t in self._requests[key] if t >= cutoff]

        return max(0, max_requests - len(self._requests[key]))


def generate_request_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for request verification."""
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_request_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature."""
    expected = generate_request_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


audit_logger = AuditLogger()
rate_limiter = RateLimiter()
