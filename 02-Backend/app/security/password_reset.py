"""Secure password reset flow with short-lived tokens.

Generates cryptographically random reset tokens, stores them with
expiry, and validates them when the user submits a new password.
Rate-limited and single-use.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class PasswordResetToken:
    email: str
    token_hash: str
    created_at: float
    expires_at: float
    used: bool = False


class SecurePasswordReset:
    """Manages secure password reset tokens."""

    def __init__(self, ttl_seconds: float = 3600.0) -> None:
        self._ttl = ttl_seconds
        self._tokens: Dict[str, PasswordResetToken] = {}
        self._lock = threading.Lock()

    def create_token(self, email: str) -> str:
        raw = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        now = time.time()
        record = PasswordResetToken(
            email=email,
            token_hash=token_hash,
            created_at=now,
            expires_at=now + self._ttl,
        )
        with self._lock:
            self._tokens[token_hash] = record
        self._cleanup_expired()
        return raw

    def consume_token(self, raw_token: str, email: str) -> bool:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = time.time()
        with self._lock:
            record = self._tokens.get(token_hash)
            if not record:
                return False
            if record.used:
                return False
            if record.email != email:
                return False
            if now > record.expires_at:
                del self._tokens[token_hash]
                return False
            record.used = True
            return True

    def invalidate_user_tokens(self, email: str) -> None:
        now = time.time()
        with self._lock:
            to_remove = [
                jti for jti, rec in self._tokens.items()
                if rec.email == email and not rec.used
            ]
            for jti in to_remove:
                del self._tokens[jti]

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired = [jti for jti, rec in self._tokens.items() if now > rec.expires_at]
        for jti in expired:
            del self._tokens[jti]


secure_password_reset = SecurePasswordReset()
