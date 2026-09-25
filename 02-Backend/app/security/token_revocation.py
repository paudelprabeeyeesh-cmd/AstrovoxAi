"""Token revocation list for immediate JWT/session invalidation.

Maintains an in-memory revocation store with TTL support.
Revoked tokens are rejected even if their signature is valid.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RevokedToken:
    jti: str
    user_id: str
    revoked_at: float
    expires_at: float
    reason: str = "logout"


class TokenRevocationList:
    """In-memory token revocation list with automatic expiry cleanup."""

    def __init__(self) -> None:
        self._revoked: Dict[str, RevokedToken] = {}
        self._lock = threading.Lock()

    def revoke(self, jti: str, user_id: str, expires_at: float, reason: str = "logout") -> None:
        now = time.time()
        with self._lock:
            self._revoked[jti] = RevokedToken(
                jti=jti,
                user_id=user_id,
                revoked_at=now,
                expires_at=expires_at,
                reason=reason,
            )
        logger.info("Token revoked jti=%s user=%s reason=%s", jti, user_id, reason)

    def revoke_all_for_user(self, user_id: str, token_jtis: list[str], reason: str = "password_change") -> None:
        for jti in token_jtis:
            self.revoke(jti, user_id, time.time() + 86400, reason)

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            entry = self._revoked.get(jti)
            if not entry:
                return False
            if time.time() > entry.expires_at + 60:
                del self._revoked[jti]
                return False
            return True

    def cleanup_expired(self) -> None:
        now = time.time()
        with self._lock:
            expired = [jti for jti, entry in self._revoked.items() if now > entry.expires_at + 60]
            for jti in expired:
                del self._revoked[jti]

    def count(self) -> int:
        with self._lock:
            return len(self._revoked)


token_revocation_list = TokenRevocationList()
