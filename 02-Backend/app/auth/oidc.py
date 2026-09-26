"""OpenID Connect (OIDC) provider."""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import secrets


@dataclass
class OIDCConfig:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str
    client_id: str
    client_secret: str
    redirect_uri: str
    scopes: list[str] = None

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["openid", "profile", "email"]


class OIDCProvider:
    _configs: Dict[str, OIDCConfig] = {}
    _nonces: Dict[str, datetime] = {}

    @classmethod
    def register(cls, name: str, config: OIDCConfig) -> None:
        cls._configs[name] = config

    @classmethod
    def get(cls, name: str) -> Optional[OIDCConfig]:
        return cls._configs.get(name)

    @classmethod
    def generate_nonce(cls) -> str:
        nonce = secrets.token_urlsafe(32)
        cls._nonces[nonce] = datetime.now(timezone.utc)
        return nonce

    @classmethod
    def validate_nonce(cls, nonce: str, max_age: int = 600) -> bool:
        if nonce not in cls._nonces:
            return False
        created = cls._nonces[nonce]
        if (datetime.now(timezone.utc) - created).total_seconds() > max_age:
            del cls._nonces[nonce]
            return False
        del cls._nonces[nonce]
        return True

    @classmethod
    def build_auth_url(cls, name: str, state: str, nonce: str) -> str:
        config = cls.get(name)
        if not config:
            raise ValueError(f"OIDC config not found: {name}")
        params = {
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(config.scopes),
            "state": state,
            "nonce": nonce,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{config.authorization_endpoint}?{query}"
