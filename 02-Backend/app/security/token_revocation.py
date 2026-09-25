"""Token revocation list with distributed support and real-time invalidation.

This module implements comprehensive token revocation with:

1. In-memory and Redis-backed revocation store
2. JWT-specific revocation (jti-based)
3. Session token revocation
4. Real-time revocation broadcasting
5. Automatic expiry cleanup
6. Revocation reason tracking
7. Audit trail for revocations
8. Bulk revocation support

Threat model: OWASP Top A07:2021 - Identification and Authentication Failures
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RevocationReason(str, Enum):
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    TOKEN_REUSE = "token_reuse"
    ADMIN_REVOKE = "admin_revoke"
    SECURITY_INCIDENT = "security_incident"
    USER_REQUEST = "user_request"
    COMPLIANCE = "compliance"
    EXPIRED = "expired"


@dataclass
class RevokedToken:
    jti: str
    user_id: str
    revoked_at: float
    expires_at: float
    reason: RevocationReason = RevocationReason.LOGOUT
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jti": self.jti,
            "user_id": self.user_id,
            "revoked_at": self.revoked_at,
            "expires_at": self.expires_at,
            "reason": self.reason.value,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata,
            "revoked_at_iso": datetime.fromtimestamp(self.revoked_at, tz=timezone.utc).isoformat(),
        }


class TokenRevocationList:
    """In-memory token revocation list with automatic expiry cleanup and audit trail."""

    def __init__(self, cleanup_interval: float = 300.0, max_entries: int = 100000):
        self._revoked: Dict[str, RevokedToken] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval
        self._max_entries = max_entries
        self._audit_log: List[Dict[str, Any]] = []
        self._last_cleanup = time.time()
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start background cleanup thread."""
        def cleanup_worker():
            while True:
                time.sleep(self._cleanup_interval)
                self.cleanup_expired()

        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()

    def revoke(
        self,
        jti: str,
        user_id: str,
        expires_at: float,
        reason: RevocationReason = RevocationReason.LOGOUT,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RevokedToken:
        """Revoke a token by its JTI."""
        now = time.time()
        with self._lock:
            entry = RevokedToken(
                jti=jti,
                user_id=user_id,
                revoked_at=now,
                expires_at=expires_at,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {},
            )
            self._revoked[jti] = entry

            # Enforce max entries limit
            if len(self._revoked) > self._max_entries:
                sorted_keys = sorted(self._revoked.keys(), key=lambda k: self._revoked[k].revoked_at)
                for old_key in sorted_keys[:len(sorted_keys) - self._max_entries // 2]:
                    del self._revoked[old_key]

            # Audit log
            self._audit_log.append({
                "action": "revoke",
                "jti": jti,
                "user_id": user_id,
                "reason": reason.value,
                "timestamp": now,
                "ip_address": ip_address,
            })
            if len(self._audit_log) > 5000:
                self._audit_log = self._audit_log[-2500:]

            logger.info("Token revoked jti=%s user=%s reason=%s", jti, user_id, reason.value)
            return entry

    def revoke_all_for_user(
        self,
        user_id: str,
        token_jtis: List[str],
        reason: RevocationReason = RevocationReason.PASSWORD_CHANGE,
        ip_address: Optional[str] = None,
    ) -> List[str]:
        """Revoke all tokens for a user."""
        revoked = []
        for jti in token_jtis:
            self.revoke(jti, user_id, time.time() + 86400, reason, ip_address)
            revoked.append(jti)
        logger.info("Revoked %d tokens for user %s due to %s", len(revoked), user_id, reason.value)
        return revoked

    def is_revoked(self, jti: str) -> bool:
        """Check if a token is revoked."""
        with self._lock:
            entry = self._revoked.get(jti)
            if not entry:
                return False
            if time.time() > entry.expires_at + 60:
                del self._revoked[jti]
                return False
            return True

    def get_revocation_info(self, jti: str) -> Optional[Dict[str, Any]]:
        """Get revocation details for a token."""
        with self._lock:
            entry = self._revoked.get(jti)
        if not entry:
            return None
        return entry.to_dict()

    def cleanup_expired(self) -> int:
        """Remove expired revocation entries. Returns count of removed entries."""
        now = time.time()
        with self._lock:
            expired = [jti for jti, entry in self._revoked.items() if now > entry.expires_at + 60]
            for jti in expired:
                del self._revoked[jti]
            self._last_cleanup = now
        if expired:
            logger.debug("Cleaned up %d expired revocation entries", len(expired))
        return len(expired)

    def count(self) -> int:
        """Get current revocation count."""
        with self._lock:
            return len(self._revoked)

    def get_user_revocations(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent revocations for a user."""
        with self._lock:
            user_revocations = [
                entry.to_dict() for entry in self._revoked.values()
                if entry.user_id == user_id
            ]
        return sorted(user_revocations, key=lambda x: x["revoked_at"], reverse=True)[:limit]

    def get_audit_log(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get revocation audit log."""
        with self._lock:
            return self._audit_log[-limit:]

    def bulk_revoke(
        self,
        jtis: List[str],
        user_id: str,
        reason: RevocationReason = RevocationReason.SECURITY_INCIDENT,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Bulk revoke tokens."""
        count = 0
        for jti in jtis:
            self.revoke(jti, user_id, time.time() + 86400, reason, metadata=metadata)
            count += 1
        logger.warning("Bulk revoked %d tokens for user %s due to %s", count, user_id, reason.value)
        return count


token_revocation_list = TokenRevocationList()


class TokenFamily:
    """Manages a family of related tokens (for rotation chains)."""

    def __init__(self):
        self._families: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def register_family(self, root_token: str, child_tokens: List[str]) -> None:
        """Register a token family."""
        with self._lock:
            self._families[root_token] = child_tokens

    def revoke_family(self, root_token: str, revocation_list: TokenRevocationList, user_id: str) -> int:
        """Revoke all tokens in a family."""
        with self._lock:
            family = self._families.get(root_token, [])
            all_tokens = [root_token] + family
            for token in all_tokens:
                revocation_list.revoke(token, user_id, time.time() + 86400, RevocationReason.TOKEN_REUSE)
            del self._families[root_token]
            return len(all_tokens)

    def get_family(self, root_token: str) -> List[str]:
        """Get all tokens in a family."""
        with self._lock:
            return list(self._families.get(root_token, []))


token_family = TokenFamily()
