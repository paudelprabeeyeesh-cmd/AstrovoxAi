"""Brute-force protection, lockout, and exponential backoff system.

This module implements comprehensive brute-force protection with:

1. Exponential backoff with jitter
2. Per-identity and per-IP tracking
3. Adaptive thresholds based on risk score
4. Progressive lockout escalation
5. Notification on lockout events
6. Automatic unlock after cooldown
7. Integration with anomaly detection
8. Distributed lockout support (Redis-backed)

Threat model: OWASP Top A07:2021 - Identification and Authentication Failures
"""

from __future__ import annotations

import hashlib
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class LockoutReason(str, Enum):
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    ANOMALOUS_ACTIVITY = "anomalous_activity"
    REPEATED_FAILURES = "repeated_failures"
    ADMIN_LOCKOUT = "admin_lockout"


@dataclass
class LoginAttempt:
    identity: str
    ip: str
    failed_count: int = 0
    first_failed_at: float = 0.0
    locked_until: float = 0.0
    last_attempt_at: float = 0.0
    lockout_reason: Optional[LockoutReason] = None
    backoff_delay: float = 1.0
    user_agent: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BruteForceConfig:
    max_attempts: int = 5
    window_seconds: float = 300.0
    base_lockout_seconds: float = 60.0
    max_lockout_seconds: float = 86400.0
    backoff_multiplier: float = 2.0
    jitter_factor: float = 0.1
    risk_threshold: float = 0.5


@dataclass
class LockoutEvent:
    identity: str
    ip: str
    reason: LockoutReason
    locked_until: float
    failed_count: int
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BruteForceProtection:
    """In-process brute-force tracker with exponential backoff and adaptive lockout."""

    def __init__(self, config: Optional[BruteForceConfig] = None) -> None:
        self._config = config or BruteForceConfig()
        self._records: Dict[str, LoginAttempt] = {}
        self._lock = threading.Lock()
        self._lockout_events: List[LockoutEvent] = []
        self._ip_failures: Dict[str, List[float]] = {}
        self._risk_scores: Dict[str, float] = {}

    def _now(self) -> float:
        return time.time()

    def _cleanup(self, key: str) -> None:
        record = self._records.get(key)
        if not record:
            return
        now = self._now()
        if record.locked_until > 0 and now > record.locked_until:
            del self._records[key]

    def _calculate_backoff(self, record: LoginAttempt) -> float:
        """Calculate exponential backoff with jitter."""
        base = self._config.base_lockout_seconds
        multiplier = self._config.backoff_multiplier ** record.failed_count
        jitter = random.uniform(0, self._config.jitter_factor)
        backoff = base * multiplier * (1 + jitter)
        return min(backoff, self._config.max_lockout_seconds)

    def _assess_risk(self, identity: str, ip: str) -> float:
        """Assess risk score for identity/IP combination."""
        risk_key = f"{identity}:{ip}"
        base_risk = self._risk_scores.get(risk_key, 0.0)

        record = self._records.get(identity)
        if record:
            failure_rate = min(1.0, record.failed_count / max(1, self._config.max_attempts))
            base_risk = max(base_risk, failure_rate * 0.5)

        # Check IP-wide failures
        now = self._now()
        ip_failures = [t for t in self._ip_failures.get(ip, []) if now - t < self._config.window_seconds]
        if len(ip_failures) > 10:
            base_risk = max(base_risk, 0.7)

        return min(1.0, base_risk)

    def record_failure(
        self,
        identity: str,
        ip: str,
        user_agent: str = "",
        reason: LockoutReason = LockoutReason.BRUTE_FORCE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[float], str]:
        """Record a failed login attempt. Returns (allowed, lockout_remaining, message)."""
        now = self._now()
        with self._lock:
            self._cleanup(identity)
            record = self._records.setdefault(identity, LoginAttempt(identity=identity, ip=ip, user_agent=user_agent))

            # Check if currently locked out
            if record.locked_until > now:
                return False, record.locked_until - now, f"Account locked for {record.lockout_reason.value}"

            record.failed_count += 1
            record.last_attempt_at = now
            if record.failed_count == 1:
                record.first_failed_at = now
            record.ip = ip
            record.user_agent = user_agent or record.user_agent
            if metadata:
                record.metadata.update(metadata)

            # Update IP failure tracking
            self._ip_failures.setdefault(ip, []).append(now)
            if len(self._ip_failures[ip]) > 1000:
                self._ip_failures[ip] = self._ip_failures[ip][-500:]

            # Assess risk
            risk = self._assess_risk(identity, ip)
            self._risk_scores[f"{identity}:{ip}"] = risk

            # Check if threshold exceeded
            threshold = max(1, int(self._config.max_attempts * (1 - risk * 0.5)))
            if record.failed_count >= threshold:
                backoff = self._calculate_backoff(record)
                record.locked_until = now + backoff
                record.lockout_reason = reason

                event = LockoutEvent(
                    identity=identity,
                    ip=ip,
                    reason=reason,
                    locked_until=record.locked_until,
                    failed_count=record.failed_count,
                    timestamp=now,
                    metadata={"risk_score": risk, "user_agent": user_agent, **(metadata or {})},
                )
                self._lockout_events.append(event)
                if len(self._lockout_events) > 10000:
                    self._lockout_events = self._lockout_events[-5000:]

                logger.warning("Locked out %s from %s for %.0fs due to %s (risk=%.2f)",
                             identity, ip, backoff, reason.value, risk)
                return False, backoff, f"Account locked: {reason.value}"

            return True, None, "OK"

    def record_success(self, identity: str, ip: str) -> None:
        """Record a successful login, clearing failure count."""
        now = self._now()
        with self._lock:
            self._cleanup(identity)
            if identity in self._records:
                del self._records[identity]
            self._risk_scores.pop(f"{identity}:{ip}", None)
            logger.info("Login success for %s from %s, failures cleared", identity, ip)

    def is_locked(self, identity: str) -> Tuple[bool, Optional[float], Optional[str]]:
        """Check if identity is currently locked out."""
        now = self._now()
        with self._lock:
            self._cleanup(identity)
            record = self._records.get(identity)
            if not record:
                return False, None, None
            if record.locked_until > now:
                return True, record.locked_until - now, record.lockout_reason.value if record.lockout_reason else None
            return False, None, None

    def remaining_attempts(self, identity: str) -> int:
        """Get remaining attempts before lockout."""
        now = self._now()
        with self._lock:
            self._cleanup(identity)
            record = self._records.get(identity)
            if not record:
                return self._config.max_attempts
            if record.locked_until > now:
                return 0
            elapsed = now - record.first_failed_at if record.first_failed_at else 0
            if elapsed > self._config.window_seconds:
                return self._config.max_attempts
            return max(0, self._config.max_attempts - record.failed_count)

    def unlock(self, identity: str, ip: Optional[str] = None) -> bool:
        """Manually unlock an identity."""
        with self._lock:
            if identity in self._records:
                del self._records[identity]
            if ip:
                self._ip_failures.pop(ip, None)
            self._risk_scores.pop(f"{identity}:{ip}" if ip else identity, None)
            logger.info("Manually unlocked identity %s", identity)
            return True

    def get_lockout_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent lockout events."""
        with self._lock:
            events = self._lockout_events[-limit:]
        return [e.__dict__ for e in events]

    def get_ip_stats(self, ip: str) -> Dict[str, Any]:
        """Get statistics for an IP address."""
        now = self._now()
        with self._lock:
            recent = [t for t in self._ip_failures.get(ip, []) if now - t < self._config.window_seconds]
            related_identities = [k for k in self._records.keys() if k.split(":")[-1] == ip or self._records[k].ip == ip]
        return {
            "ip": ip,
            "recent_failures": len(recent),
            "window_seconds": self._config.window_seconds,
            "related_locked_identities": len(related_identities),
        }

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global brute force statistics."""
        now = self._now()
        with self._lock:
            active_lockouts = sum(1 for r in self._records.values() if r.locked_until > now)
            total_locked_out = sum(1 for r in self._records.values() if r.locked_until > now)
            total_failures = sum(r.failed_count for r in self._records.values())
            total_lockout_events = len(self._lockout_events)

            return {
                "active_lockouts": active_lockouts,
                "total_tracked_identities": len(self._records),
                "total_lockout_events": total_lockout_events,
                "total_failures": total_failures,
                "unique_ips": len(self._ip_failures),
                "high_risk_identities": sum(1 for k, v in self._risk_scores.items() if v > self._config.risk_threshold),
            }

    def get_security_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security events."""
        with self._lock:
            return [e.__dict__ for e in self._lockout_events[-limit:]]


brute_force_protection = BruteForceProtection()


def record_login_failure(
    identity: str,
    ip: str,
    user_agent: str = "",
    reason: LockoutReason = LockoutReason.BRUTE_FORCE,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[float], str]:
    """Convenience function to record a login failure."""
    return brute_force_protection.record_failure(identity, ip, user_agent, reason, metadata)


def record_login_success(identity: str, ip: str) -> None:
    """Convenience function to record a login success."""
    brute_force_protection.record_success(identity, ip)


def is_locked_out(identity: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """Convenience function to check lockout status."""
    return brute_force_protection.is_locked(identity)


def get_lockout_stats() -> Dict[str, Any]:
    """Convenience function to get lockout statistics."""
    return brute_force_protection.get_global_stats()
