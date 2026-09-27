"""Authentication service with JWT and password hashing."""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext
from pydantic import EmailStr, ValidationError

from .models import TokenPayload, UserCreate, UserResponse

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self) -> None:
        self._secret_key = os.getenv("SECRET_KEY", "astrovox-ai-secret-key-change-in-production")
        self._algorithm = os.getenv("ALGORITHM", "HS256")
        self._access_token_expire = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self._refresh_token_expire = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        self._revoked_tokens: set[str] = set()

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, user_id: str, scopes: list[str] | None = None) -> str:
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(minutes=self._access_token_expire),
            iat=now,
            scope=scopes or ["access"],
            jti=secrets.token_urlsafe(16),
        )
        return jwt.encode(payload.model_dump(), self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = TokenPayload(
            sub=user_id,
            exp=now + timedelta(days=self._refresh_token_expire),
            iat=now,
            scope=["refresh"],
            jti=secrets.token_urlsafe(16),
        )
        return jwt.encode(payload.model_dump(), self._secret_key, algorithm=self._algorithm)

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self._algorithm])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None
        except ValidationError as exc:
            logger.warning("Token validation error: %s", exc)
            return None

    def revoke_token(self, token: str) -> None:
        self._revoked_tokens.add(token)

    def is_revoked(self, token: str) -> bool:
        return token in self._revoked_tokens

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
