import json
import time
import logging
import secrets
import hashlib
import base64
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)


class AuthProviderType(Enum):
    OAUTH2 = "oauth2"
    SAML = "saml"
    JWT = "jwt"
    API_KEY = "api_key"
    BASIC = "basic"


@dataclass
class ProviderConfig:
    provider_id: str
    provider_type: AuthProviderType
    client_id: str
    client_secret: str
    authorize_url: str = ""
    token_url: str = ""
    scopes: List[str] = field(default_factory=list)
    redirect_uri: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthToken:
    access_token: str
    token_type: str = "Bearer"
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    issued_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ThirdPartyAuthAdapter:
    def __init__(self, base_url: str = "https://api.astrovox.ai/v1"):
        self.base_url = base_url.rstrip('/')
        self.providers: Dict[str, ProviderConfig] = {}
        self._tokens: Dict[str, AuthToken] = {}
        self._pkce_challenges: Dict[str, str] = {}

    def register_provider(self, config: ProviderConfig):
        self.providers[config.provider_id] = config
        logger.info(f"Registered auth provider: {config.provider_id} ({config.provider_type.value})")

    def get_authorization_url(self, provider_id: str, state: Optional[str] = None) -> str:
        config = self.providers.get(provider_id)
        if not config:
            raise ValueError(f"Provider {provider_id} not registered")
        if config.provider_type != AuthProviderType.OAUTH2:
            raise ValueError(f"Provider {provider_id} is not OAuth2")
        state = state or secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "state": state,
        }
        if config.scopes:
            params["scope"] = " ".join(config.scopes)
        challenge, verifier = self._generate_pkce()
        self._pkce_challenges[state] = verifier
        params["code_challenge"] = challenge
        params["code_challenge_method"] = "S256"
        return f"{config.authorize_url}?{urlencode(params)}"

    def exchange_code(self, provider_id: str, code: str, state: str) -> AuthToken:
        config = self.providers.get(provider_id)
        if not config:
            raise ValueError(f"Provider {provider_id} not registered")
        verifier = self._pkce_challenges.pop(state, None)
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
            "redirect_uri": config.redirect_uri,
        }
        if verifier:
            data["code_verifier"] = verifier
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        token = AuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope")
        )
        self._tokens[provider_id] = token
        return token

    def refresh_token(self, provider_id: str) -> AuthToken:
        config = self.providers.get(provider_id)
        token = self._tokens.get(provider_id)
        if not config or not token or not token.refresh_token:
            raise ValueError(f"No refresh token available for {provider_id}")
        data = {
            "grant_type": "refresh_token",
            "refresh_token": token.refresh_token,
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
        response = requests.post(config.token_url, data=data, timeout=30)
        response.raise_for_status()
        token_data = response.json()
        token = AuthToken(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in"),
            refresh_token=token_data.get("refresh_token", token.refresh_token),
            scope=token_data.get("scope")
        )
        self._tokens[provider_id] = token
        return token

    def get_valid_token(self, provider_id: str) -> Optional[str]:
        token = self._tokens.get(provider_id)
        if not token:
            return None
        if token.expires_in:
            issued = datetime.fromisoformat(token.issued_at)
            if datetime.utcnow() > issued + timedelta(seconds=token.expires_in - 60):
                try:
                    token = self.refresh_token(provider_id)
                except Exception as e:
                    logger.error(f"Token refresh failed for {provider_id}: {e}")
                    return None
        return token.access_token

    def build_api_headers(self, provider_id: str) -> Dict[str, str]:
        token = self.get_valid_token(provider_id)
        if not token:
            raise ValueError(f"No valid token for provider {provider_id}")
        return {"Authorization": f"Bearer {token}"}

    def _generate_pkce(self) -> Tuple[str, str]:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('utf-8')).digest()
        ).rstrip(b'=').decode('utf-8')
        return challenge, verifier
