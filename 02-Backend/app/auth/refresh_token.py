"""Refresh token rotation for secure session management."""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
import secrets
import hashlib
from dataclasses import dataclass


@dataclass
class RefreshToken:
    token_hash: str
    user_id: str
    expires_at: datetime
    family_id: str
    previous_token: Optional[str] = None
    used: bool = False


class RefreshTokenRotation:
    _tokens: Dict[str, RefreshToken] = {}
    _families: Dict[str, list[str]] = {}

    @classmethod
    def create_token(cls, user_id: str, expires_days: int = 30) -> Tuple[str, RefreshToken]:
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        family_id = secrets.token_urlsafe(16)
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        token = RefreshToken(
            token_hash=token_hash,
            user_id=user_id,
            expires_at=expires_at,
            family_id=family_id,
        )
        cls._tokens[token_hash] = token
        if family_id not in cls._families:
            cls._families[family_id] = []
        cls._families[family_id].append(token_hash)
        return raw_token, token

    @classmethod
    def rotate(cls, raw_token: str) -> Optional[Tuple[str, RefreshToken]]:
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token = cls._tokens.get(token_hash)
        if not token or token.used:
            return None
        if token.expires_at < datetime.now(timezone.utc):
            return None
        token.used = True
        return cls.create_token(token.user_id)

    @classmethod
    def revoke_family(cls, family_id: str) -> None:
        for token_hash in cls._families.get(family_id, []):
            if token_hash in cls._tokens:
                cls._tokens[token_hash].used = True
