"""Layer 1 — Identity & Authentication: Argon2, session revocation, device management."""

import time
import secrets
import hashlib
import logging
import re
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PasswordHasher:
    """Argon2 password hashing with fallback."""

    def __init__(self):
        self._hasher = None
        self._init_hasher()

    def _init_hasher):
        try:
            from argon2 import PasswordHasher as Argon2Hasher
            from argon2.exceptions import VerifyMismatchError
            self._hasher = Argon2Hasher(
                time_cost=3,
                memory_cost=65536,
                parallelism=4,
                hash_len=32,
                salt_len=16,
            )
            self._backend = "argon2"
        except ImportError:
            self._backend = "pbkdf2"

    def hash(self, password: str) -> str:
        """Hash a password."""
        if not password:
            raise ValueError("Password cannot be empty")

        if self._backend == "argon2":
            return f"argon2:{self._hasher.hash(password)}"
        else:
            salt = secrets.token_hex(16)
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000)
            return f"pbkdf2:{salt}:{hash_obj.hex()}"

    def verify(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        if not password or not hashed:
            return False

        try:
            if hashed.startswith("argon2:"):
                if self._backend != "argon2":
                    return False
                return self._hasher.verify(hashed[7:], password)
            elif hashed.startswith("pbkdf2:"):
                parts = hashed.split(":")
                if len(parts) != 3:
                    return False
                salt, stored_hash = parts[1], parts[2]
                hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 600000)
                return hash_obj.hex() == stored_hash
            return False
        except Exception:
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if a hash needs to be upgraded."""
        if self._backend == "argon2" and hashed.startswith("pbkdf2:"):
            return True
        return False


@dataclass
class DeviceInfo:
    """Device information for session management."""
    device_id: str
    user_agent: str
    ip_address: str
    fingerprint: str
    first_seen: float
    last_seen: float
    is_trusted: bool = False
    is_blocked: bool = False


@dataclass
class SessionInfo:
    """Enhanced session information."""
    session_id: str
    user_id: str
    device_id: str
    ip_address: str
    user_agent: str
    created_at: float
    expires_at: float
    last_activity: float
    is_active: bool = True
    is_revoked: bool = False


class DeviceManager:
    """Manage user devices."""

    def __init__(self):
        self._devices: dict[str, dict[str, DeviceInfo]] = {}

    def register_device(self, user_id: str, user_agent: str, ip_address: str) -> DeviceInfo:
        """Register or update a device."""
        fingerprint = hashlib.sha256(f"{user_agent}:{ip_address}".encode()).hexdigest()[:16]
        device_id = f"dev_{fingerprint}"
        now = time.time()

        if user_id not in self._devices:
            self._devices[user_id] = {}

        existing = self._devices[user_id].get(device_id)
        if existing:
            existing.last_seen = now
            return existing

        device = DeviceInfo(
            device_id=device_id,
            user_agent=user_agent,
            ip_address=ip_address,
            fingerprint=fingerprint,
            first_seen=now,
            last_seen=now,
        )
        self._devices[user_id][device_id] = device
        return device

    def get_devices(self, user_id: str) -> list[DeviceInfo]:
        """Get all devices for a user."""
        return list(self._devices.get(user_id, {}).values())

    def trust_device(self, user_id: str, device_id: str, trusted: bool = True):
        """Mark a device as trusted or untrusted."""
        device = self._devices.get(user_id, {}).get(device_id)
        if device:
            device.is_trusted = trusted

    def block_device(self, user_id: str, device_id: str, blocked: bool = True):
        """Block or unblock a device."""
        device = self._devices.get(user_id, {}).get(device_id)
        if device:
            device.is_blocked = blocked

    def is_device_blocked(self, user_id: str, device_id: str) -> bool:
        """Check if a device is blocked."""
        device = self._devices.get(user_id, {}).get(device_id)
        return device.is_blocked if device else False

    def remove_device(self, user_id: str, device_id: str):
        """Remove a device."""
        if user_id in self._devices:
            self._devices[user_id].pop(device_id, None)


class SessionRevocationList:
    """Manage revoked sessions."""

    def __init__(self):
        self._revoked: dict[str, float] = {}

    def revoke(self, session_id: str, reason: str = ""):
        """Revoke a session."""
        self._revoked[session_id] = time.time()
        logger.info(f"Session revoked: {session_id}, reason: {reason}")

    def is_revoked(self, session_id: str) -> bool:
        """Check if a session is revoked."""
        return session_id in self._revoked

    def cleanup(self, max_age: int = 86400):
        """Remove old revocation entries."""
        cutoff = time.time() - max_age
        expired = [sid for sid, ts in self._revoked.items() if ts < cutoff]
        for sid in expired:
            del self._revoked[sid]


class LoginAlertManager:
    """Monitor and alert on suspicious login activity."""

    def __init__(self):
        self._login_history: dict[str, list[dict]] = {}
        self._alerts: list[dict] = []

    def record_login(self, user_id: str, ip: str, user_agent: str, success: bool):
        """Record a login attempt."""
        if user_id not in self._login_history:
            self._login_history[user_id] = []

        entry = {
            "ip": ip,
            "user_agent": user_agent,
            "success": success,
            "timestamp": time.time(),
        }
        self._login_history[user_id].append(entry)

        if len(self._login_history[user_id]) > 100:
            self._login_history[user_id] = self._login_history[user_id][-100:]

        if not success:
            self._check_suspicious(user_id, ip)

    def _check_suspicious(self, user_id: str, ip: str):
        """Check for suspicious activity."""
        history = self._login_history.get(user_id, [])
        recent_failures = [
            h for h in history
            if not h["success"] and time.time() - h["timestamp"] < 300
        ]

        if len(recent_failures) >= 5:
            self._alerts.append({
                "type": "multiple_failed_logins",
                "user_id": user_id,
                "ip": ip,
                "count": len(recent_failures),
                "timestamp": time.time(),
            })

        unique_ips = set(h["ip"] for h in history[-10:])
        if len(unique_ips) > 3:
            self._alerts.append({
                "type": "multiple_ips",
                "user_id": user_id,
                "ips": list(unique_ips),
                "timestamp": time.time(),
            })

    def get_alerts(self, since: float = 0) -> list[dict]:
        """Get security alerts."""
        return [a for a in self._alerts if a["timestamp"] >= since]

    def get_recent_logins(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get recent login history."""
        history = self._login_history.get(user_id, [])
        return history[-limit:]


password_hasher = PasswordHasher()
device_manager = DeviceManager()
session_revocation = SessionRevocationList()
login_alerts = LoginAlertManager()
