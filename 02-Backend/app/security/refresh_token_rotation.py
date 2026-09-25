"""Refresh token rotation with reuse detection and device tracking.

This module implements comprehensive refresh token rotation with:

1. Token rotation with parent-child chain tracking
2. Reuse detection (token replay attacks)
3. Device fingerprinting per token
4. Family-wide revocation on compromise
5. Time-based and usage-based expiry
6. Integration with token revocation list
7. Audit trail for all rotation events

Threat model: OWASP Top A07:2021 - Identification and Authentication Failures
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .token_revocation import RevocationReason, TokenRevocationList, TokenFamily, token_revocation_list

logger = logging.getLogger(__name__)


@dataclass
class RefreshTokenRecord:
    token: str
    user_id: str
    parent_token: Optional[str]
    created_at: float
    expires_at: float
    is_revoked: bool = False
    reuse_detected: bool = False
    device_fingerprint: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    rotation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationConfig:
    rotation_lifetime_seconds: float = 86400.0
    max_rotations_per_day: int = 50
    reuse_detection_enabled: bool = True
    device_binding_enabled: bool = True
    family_revocation_on_reuse: bool = True


class RefreshTokenRotation:
    """Manages refresh token rotation chain per user with advanced security features."""

    def __init__(self, config: Optional[RotationConfig] = None) -> None:
        self._config = config or RotationConfig()
        self._records: Dict[str, RefreshTokenRecord] = {}
        self._lock = threading.Lock()
        self._user_rotation_counts: Dict[str, List[float]] = {}
        self._rotation_audit: List[Dict[str, Any]] = []
        self._token_families = TokenFamily()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""
        def cleanup_worker():
            while True:
                time.sleep(600)
                self._cleanup_expired()

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def _cleanup_expired(self) -> None:
        """Remove expired token records."""
        now = time.time()
        with self._lock:
            expired = [jti for jti, rec in self._records.items() if now > rec.expires_at + 60]
            for jti in expired:
                del self._records[jti]

    def _record_rotation(self, old_token: Optional[str], new_token: str, user_id: str, ip_address: Optional[str]) -> None:
        """Record rotation event in audit log."""
        entry = {
            "event": "rotate",
            "old_token": old_token[:16] + "..." if old_token else None,
            "new_token": new_token[:16] + "...",
            "user_id": user_id,
            "ip_address": ip_address,
            "timestamp": time.time(),
            "rotation_count": self._records.get(new_token, RefreshTokenRecord(token=new_token, user_id=user_id, parent_token=old_token, created_at=time.time(), expires_at=time.time() + self._config.rotation_lifetime_seconds)).rotation_count,
        }
        self._rotation_audit.append(entry)
        if len(self._rotation_audit) > 10000:
            self._rotation_audit = self._rotation_audit[-5000:]

    def _check_rotation_limit(self, user_id: str) -> bool:
        """Check if user has exceeded daily rotation limit."""
        now = time.time()
        with self._lock:
            counts = self._user_rotation_counts.get(user_id, [])
            recent = [t for t in counts if now - t < 86400]
            self._user_rotation_counts[user_id] = recent
            if len(recent) >= self._config.max_rotations_per_day:
                logger.warning("User %s exceeded rotation limit: %d in 24h", user_id, len(recent))
                return False
            recent.append(now)
            return True

    def generate(
        self,
        user_id: str,
        parent_token: Optional[str] = None,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """Generate a new refresh token."""
        now = time.time()
        raw_token = secrets.token_urlsafe(48)
        record = RefreshTokenRecord(
            token=raw_token,
            user_id=user_id,
            parent_token=parent_token,
            created_at=now,
            expires_at=now + self._config.rotation_lifetime_seconds,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        with self._lock:
            self._records[raw_token] = record

        # Register in family
        if parent_token:
            self._token_families.register_family(parent_token, [raw_token])

        logger.debug("Generated refresh token for user %s", user_id)
        return raw_token

    def rotate(
        self,
        old_token: str,
        user_id: str,
        device_fingerprint: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Rotate an old token, returning the new token and whether rotation was successful."""
        now = time.time()
        with self._lock:
            old_record = self._records.get(old_token)

            if not old_record:
                # Token not found - could be reuse attempt or expired
                new_token = self.generate(user_id, parent_token=old_token, device_fingerprint=device_fingerprint, ip_address=ip_address, user_agent=user_agent)
                return new_token, False

            if old_record.is_revoked or old_record.reuse_detected:
                logger.warning("Reuse detected for token of user %s", user_id)
                self._revoke_chain(old_token, user_id)
                raise ValueError("Refresh token reuse detected - all sessions revoked")

            if old_record.user_id != user_id:
                self._revoke_chain(old_token, user_id)
                raise ValueError("Token user mismatch")

            # Check device binding
            if self._config.device_binding_enabled and old_record.device_fingerprint:
                if device_fingerprint and old_record.device_fingerprint != device_fingerprint:
                    logger.warning("Device fingerprint mismatch for user %s", user_id)
                    self._revoke_chain(old_token, user_id)
                    raise ValueError("Device fingerprint mismatch")

            # Check rotation limit
            if not self._check_rotation_limit(user_id):
                raise ValueError("Rotation rate limit exceeded")

            old_record.is_revoked = True
            old_record.reuse_detected = False

            new_token = secrets.token_urlsafe(48)
            new_record = RefreshTokenRecord(
                token=new_token,
                user_id=user_id,
                parent_token=old_token,
                created_at=now,
                expires_at=now + self._config.rotation_lifetime_seconds,
                device_fingerprint=device_fingerprint or old_record.device_fingerprint,
                ip_address=ip_address or old_record.ip_address,
                user_agent=user_agent or old_record.user_agent,
                rotation_count=old_record.rotation_count + 1,
            )
            self._records[new_token] = new_record

            # Revoke old token
            token_revocation_list.revoke(
                jti=old_token,
                user_id=user_id,
                expires_at=old_record.expires_at,
                reason=RevocationReason.LOGOUT,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            self._record_rotation(old_token, new_token, user_id, ip_address)

            # Register family
            self._token_families.register_family(old_token, [new_token])

            logger.debug("Rotated refresh token for user %s", user_id)
            return new_token, True

    def _revoke_chain(self, start_token: str, user_id: str) -> None:
        """Revoke entire token chain."""
        visited: set = set()
        stack = [start_token]
        revoked_count = 0
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            record = self._records.get(current)
            if record and record.user_id == user_id:
                record.is_revoked = True
                record.reuse_detected = True
                token_revocation_list.revoke(
                    jti=current,
                    user_id=user_id,
                    expires_at=record.expires_at,
                    reason=RevocationReason.TOKEN_REUSE,
                    ip_address=record.ip_address,
                    user_agent=record.user_agent,
                    metadata={"reuse_detected": True, "rotation_count": record.rotation_count},
                )
                revoked_count += 1
                if record.parent_token and record.parent_token not in visited:
                    stack.append(record.parent_token)

        logger.warning("Revoked %d tokens in chain for user %s starting from %s", revoked_count, user_id, start_token[:16])

    def validate(self, token: str, user_id: str, device_fingerprint: Optional[str] = None) -> bool:
        """Validate a refresh token."""
        with self._lock:
            record = self._records.get(token)
            if not record:
                return False
            if record.is_revoked or record.reuse_detected:
                return False
            if record.user_id != user_id:
                return False
            if time.time() > record.expires_at:
                return False
            if self._config.device_binding_enabled and record.device_fingerprint:
                if device_fingerprint and record.device_fingerprint != device_fingerprint:
                    return False
            return True

    def revoke_all(self, user_id: str, reason: RevocationReason = RevocationReason.PASSWORD_CHANGE) -> int:
        """Revoke all active refresh tokens for a user."""
        now = time.time()
        with self._lock:
            to_revoke = [jti for jti, rec in self._records.items() if rec.user_id == user_id and not rec.is_revoked]
            for jti in to_revoke:
                rec = self._records[jti]
                rec.is_revoked = True
                token_revocation_list.revoke(jti, user_id, now + 86400, reason)
            logger.info("Revoked %d refresh tokens for user %s due to %s", len(to_revoke), user_id, reason.value)
            return len(to_revoke)

    def revoke_by_device(self, user_id: str, device_fingerprint: str) -> int:
        """Revoke tokens for a specific device."""
        with self._lock:
            to_revoke = [
                jti for jti, rec in self._records.items()
                if rec.user_id == user_id and rec.device_fingerprint == device_fingerprint and not rec.is_revoked
            ]
            for jti in to_revoke:
                rec = self._records[jti]
                rec.is_revoked = True
                token_revocation_list.revoke(jti, user_id, rec.expires_at, RevocationReason.ADMIN_REVOKE)
            return len(to_revoke)

    def get_user_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active tokens for a user."""
        with self._lock:
            user_tokens = [
                {
                    "token": rec.token[:16] + "...",
                    "created_at": rec.created_at,
                    "expires_at": rec.expires_at,
                    "is_revoked": rec.is_revoked,
                    "device_fingerprint": rec.device_fingerprint,
                    "ip_address": rec.ip_address,
                    "rotation_count": rec.rotation_count,
                }
                for rec in self._records.values()
                if rec.user_id == user_id
            ]
        return sorted(user_tokens, key=lambda x: x["created_at"], reverse=True)

    def get_rotation_audit(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get rotation audit log."""
        with self._lock:
            return self._rotation_audit[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get rotation statistics."""
        with self._lock:
            active = sum(1 for rec in self._records.values() if not rec.is_revoked)
            revoked = sum(1 for rec in self._records.values() if rec.is_revoked)
            reuse_detected = sum(1 for rec in self._records.values() if rec.reuse_detected)

            return {
                "total_tokens": len(self._records),
                "active_tokens": active,
                "revoked_tokens": revoked,
                "reuse_detected": reuse_detected,
                "unique_users": len(set(rec.user_id for rec in self._records.values())),
                "total_rotations": len(self._rotation_audit),
            }

    def get_user_rotation_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get rotation history for a user."""
        with self._lock:
            return [
                entry for entry in self._rotation_audit
                if entry.get("user_id") == user_id
            ][-limit:]


refresh_token_rotation = RefreshTokenRotation()


def generate_refresh_token(
    user_id: str,
    parent_token: Optional[str] = None,
    device_fingerprint: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> str:
    """Convenience function to generate a refresh token."""
    return refresh_token_rotation.generate(user_id, parent_token, device_fingerprint, ip_address, user_agent)


def rotate_refresh_token(
    old_token: str,
    user_id: str,
    device_fingerprint: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Tuple[str, bool]:
    """Convenience function to rotate a refresh token."""
    return refresh_token_rotation.rotate(old_token, user_id, device_fingerprint, ip_address, user_agent)


def revoke_all_user_tokens(user_id: str, reason: RevocationReason = RevocationReason.PASSWORD_CHANGE) -> int:
    """Convenience function to revoke all user tokens."""
    return refresh_token_rotation.revoke_all(user_id, reason)
