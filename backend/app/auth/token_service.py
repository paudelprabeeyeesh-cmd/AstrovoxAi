"""JWT token service for authentication and authorization."""
from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenPayload:
    sub: str
    exp: int
    iat: int
    scope: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TokenService:
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256") -> None:
        self._secret_key = secret_key or hashlib.sha256(b"astrovox-ai-token-service").hexdigest()
        self._algorithm = algorithm
        self._revoked: set = set()

    def encode(self, payload: TokenPayload) -> str:
        import jwt
        header = {"alg": self._algorithm, "typ": "JWT"}
        message = self._base64url(json.dumps(header)) + "." + self._base64url(json.dumps(self._payload_dict(payload)))
        signature = self._sign(message)
        return message + "." + signature

    def decode(self, token: str) -> Optional[TokenPayload]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            message = parts[0] + "." + parts[1]
            if not self._verify_signature(message, parts[2]):
                return None
            payload = json.loads(self._base64url_decode(parts[1]))
            return self._payload_from_dict(payload)
        except Exception:
            logger.exception("Failed to decode token")
            return None

    def revoke(self, token: str) -> None:
        self._revoked.add(token)

    def is_revoked(self, token: str) -> bool:
        return token in self._revoked

    def refresh(self, token: str, ttl_seconds: int = 3600) -> Optional[str]:
        payload = self.decode(token)
        if not payload:
            return None
        payload.iat = int(time.time())
        payload.exp = payload.iat + ttl_seconds
        return self.encode(payload)

    @staticmethod
    def _base64url(data: str) -> str:
        import base64
        return base64.urlsafe_b64encode(data.encode()).rstrip(b"=").decode()

    @staticmethod
    def _base64url_decode(data: str) -> str:
        import base64
        padding = 4 - len(data) % 4
        return base64.urlsafe_b64decode(data + "=" * padding).decode()

    def _sign(self, message: str) -> str:
        import hmac
        import hashlib
        return hmac.new(self._secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

    def _verify_signature(self, message: str, signature: str) -> bool:
        expected = self._sign(message)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def _payload_dict(payload: TokenPayload) -> Dict[str, Any]:
        return {
            "sub": payload.sub,
            "exp": payload.exp,
            "iat": payload.iat,
            "scope": payload.scope,
            **payload.metadata,
        }

    @staticmethod
    def _payload_from_dict(data: Dict[str, Any]) -> TokenPayload:
        metadata = {k: v for k, v in data.items() if k not in ("sub", "exp", "iat", "scope")}
        return TokenPayload(sub=data["sub"], exp=data["exp"], iat=data["iat"], scope=data.get("scope", []), metadata=metadata)


import json
import hmac

token_service = TokenService()
