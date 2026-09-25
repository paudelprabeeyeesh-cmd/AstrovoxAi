"""OAuth2 provider integrations."""

from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class OAuth2Provider(Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    APPLE = "apple"
    FACEBOOK = "facebook"


@dataclass
class OAuth2Config:
    provider: OAuth2Provider
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str] = None
    redirect_uri: str = ""

    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["openid", "profile", "email"]


class OAuth2Manager:
    _providers: Dict[OAuth2Provider, OAuth2Config] = {}

    @classmethod
    def register(cls, config: OAuth2Config) -> None:
        cls._providers[config.provider] = config

    @classmethod
    def get(cls, provider: OAuth2Provider) -> Optional[OAuth2Config]:
        return cls._providers.get(provider)

    @classmethod
    def list_providers(cls) -> list[OAuth2Provider]:
        return list(cls._providers.keys())


OAUTH2_PROVIDERS = {
    OAuth2Provider.GOOGLE: OAuth2Config(
        provider=OAuth2Provider.GOOGLE,
        client_id="",
        client_secret="",
        authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
    ),
    OAuth2Provider.GITHUB: OAuth2Config(
        provider=OAuth2Provider.GITHUB,
        client_id="",
        client_secret="",
        authorization_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        userinfo_url="https://api.github.com/user",
    ),
    OAuth2Provider.MICROSOFT: OAuth2Config(
        provider=OAuth2Provider.MICROSOFT,
        client_id="",
        client_secret="",
        authorization_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/oidc/userinfo",
    ),
}

for config in OAUTH2_PROVIDERS.values():
    OAuth2Manager.register(config)
