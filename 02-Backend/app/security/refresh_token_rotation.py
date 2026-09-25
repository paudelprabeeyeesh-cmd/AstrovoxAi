"""Refresh token rotation with reuse detection.

Every call to /auth/refresh issues a new refresh token and invalidates
the previous one. If a token is reused, all descendant tokens are
revoked and the user is logged out.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .token_revocation import token_revocation_list

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


class RefreshTokenRotation:
    """Manages refresh token rotation chain per user."""

    def __init__(self, rotation_lifetime_seconds: float = 86400.0) -> None:
        self._rotation_lifetime = rotation_lifetime_seconds
        self._records: Dict[str, RefreshTokenRecord] = {}
        self._lock = threading.Lock()

    def generate(self, user_id: str, parent_token: Optional[str] = None) -> str:
        now = time.time()
        raw_token = secrets.token_urlsafe(48)
        record = RefreshTokenRecord(
            token=raw_token,
            user_id=user_id,
            parent_token=parent_token,
            created_at=now,
            expires_at=now + self._rotation_lifetime,
        )
        with self._lock:
            self._records[raw_token] = record
        return raw_token

    def rotate(self, old_token: str, user_id: str) -> tuple[str, bool]:
        now = time.time()
        with self._lock:
            old_record = self._records.get(old_token)
            if not old_record:
                new_token = self.generate(user_id, parent_token=old_token)
                return new_token, False

            if old_record.is_revoked or old_record.reuse_detected:
                logger.warning("Reuse detected for token of user %s", user_id)
                self._revoke_chain(old_token, user_id)
                raise ValueError("Refresh token reuse detected - all sessions revoked")

            if old_record.user_id != user_id:
                self._revoke_chain(old_token, user_id)
                raise ValueError("Token user mismatch")

            old_record.is_revoked = True
            new_token = secrets.token_urlsafe(48)
            new_record = RefreshTokenRecord(
                token=new_token,
                user_id=user_id,
                parent_token=old_token,
                created_at=now,
                expires_at=now + self._rotation_lifetime,
            )
            self._records[new_token] = new_record
            return new_token, True

    def _revoke_chain(self, start_token: str, user_id: str) -> None:
        visited: set[str] = set()
        stack = [start_token]
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
                    reason="token_reuse",
                )
                if record.parent_token and record.parent_token not in visited:
                    stack.append(record.parent_token)

    def validate(self, token: str, user_id: str) -> bool:
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
            return True

    def revoke_all(self, user_id: str) -> None:
        now = time.time()
        with self._lock:
            to_revoke = [jti for jti, rec in self._records.items() if rec.user_id == user_id and not rec.is_revoked]
            for jti in to_revoke:
                self._records[jti].is_revoked = True
                token_revocation_list.revoke(jti, user_id, now + 86400, reason="password_change")


refresh_token_rotation = RefreshTokenRotation()
