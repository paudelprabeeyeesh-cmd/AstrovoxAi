"""JWT access token management."""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from dataclasses import dataclass


@dataclass
class TokenPayload:
    sub: str
    exp: datetime
    iat: datetime
    scope: str = "user"
    aud: str = "astrovox-api"


class JWTManager:
    @staticmethod
    def create_access_token(
        subject: str,
        secret_key: str,
        expires_minutes: int = 15,
        scope: str = "user",
        algorithm: str = "HS256",
        audience: str = "astrovox-api",
        issuer: str = "astrovox-auth",
    ) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "exp": now + timedelta(minutes=expires_minutes),
            "iat": now,
            "scope": scope,
            "aud": audience,
            "iss": issuer,
            "jti": secrets.token_urlsafe(16),
        }
        return jwt.encode(payload, secret_key, algorithm=algorithm)

    @staticmethod
    def decode_token(
        token: str,
        secret_key: str,
        algorithms: list[str] = None,
        audience: str = "astrovox-api",
        issuer: str = "astrovox-auth",
    ) -> Optional[Dict[str, Any]]:
        algorithms = algorithms or ["HS256"]
        try:
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=algorithms,
                audience=audience,
                issuer=issuer,
            )
            return payload
        except JWTError:
            return None

    @staticmethod
    def is_expired(payload: Dict[str, Any]) -> bool:
        exp = payload.get("exp")
        if not exp:
            return True
        return datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc)

    @staticmethod
    def is_revoked(payload: Dict[str, Any], revocation_list: Any = None) -> bool:
        jti = payload.get("jti")
        if not jti or revocation_list is None:
            return False
        return revocation_list.is_revoked(jti)
