"""AI Operating System Security."""

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"


@dataclass
class Credential:
    id: str
    method: AuthMethod
    secret: str
    owner: str
    expires_at: float | None = None
    scopes: list[str] = field(default_factory=list)


@dataclass
class Permission:
    resource: str
    action: str
    effect: str = "allow"


class Authentication:
    def __init__(self, secret_key: str | None = None) -> None:
        self._secret_key = secret_key or os.urandom(32).hex()
        self._credentials: dict[str, Credential] = {}
        self._revoked: set[str] = set()

    def register_api_key(self, owner: str, scopes: list[str] | None = None) -> Credential:
        raw = os.urandom(24).hex()
        cred = Credential(
            id=hashlib.sha256(raw.encode()).hexdigest()[:16],
            method=AuthMethod.API_KEY,
            secret=raw,
            owner=owner,
            scopes=scopes or [],
        )
        self._credentials[cred.id] = cred
        logger.info("Registered API key for %s", owner)
        return cred

    def verify(self, credential_id: str, secret: str) -> bool:
        if credential_id in self._revoked:
            return False
        cred = self._credentials.get(credential_id)
        if not cred:
            return False
        if cred.expires_at is not None and time.time() > cred.expires_at:
            self._revoked.add(credential_id)
            return False
        return hmac.compare_digest(cred.secret, secret)

    def revoke(self, credential_id: str) -> None:
        self._revoked.add(credential_id)
        logger.info("Revoked credential %s", credential_id)

    def get_credential(self, credential_id: str) -> Credential | None:
        if credential_id in self._revoked:
            return None
        return self._credentials.get(credential_id)


class Authorization:
    def __init__(self) -> None:
        self._permissions: dict[str, list[Permission]] = {}
        self._roles: dict[str, list[str]] = {}

    def grant(self, owner: str, permission: Permission) -> None:
        self._permissions.setdefault(owner, []).append(permission)

    def assign_role(self, owner: str, role: str) -> None:
        self._roles.setdefault(owner, []).append(role)

    def check(self, owner: str, resource: str, action: str) -> bool:
        perms = self._permissions.get(owner, [])
        for perm in perms:
            if perm.resource == resource and perm.action == action and perm.effect == "allow":
                return True
        for role in self._roles.get(owner, []):
            role_perms = self._permissions.get(role, [])
            for perm in role_perms:
                if perm.resource == resource and perm.action == action and perm.effect == "allow":
                    return True
        return False

    def list_permissions(self, owner: str) -> list[Permission]:
        return list(self._permissions.get(owner, []))


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._records: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        self._records.setdefault(key, [])
        self._records[key] = [t for t in self._records[key] if now - t < self._window_seconds]
        if len(self._records[key]) >= self._max_requests:
            return False
        self._records[key].append(now)
        return True


class APIGateway:
    def __init__(self, auth: Authentication, authz: Authorization) -> None:
        self._auth = auth
        self._authz = authz
        self._rate_limiter: RateLimiter | None = None
        self._routes: dict[str, dict[str, Any]] = {}

    def set_rate_limit(self, max_requests: int, window_seconds: float) -> None:
        self._rate_limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    def register_route(self, path: str, method: str, handler: Callable, required_scopes: list[str] | None = None) -> None:
        self._routes[f"{method.upper()}:{path}"] = {
            "handler": handler,
            "scopes": required_scopes or [],
        }

    def handle_request(self, method: str, path: str, credential_id: str | None = None, secret: str | None = None, **kwargs: Any) -> Any:
        route_key = f"{method.upper()}:{path}"
        if route_key not in self._routes:
            return {"error": "not_found", "status": 404}
        route = self._routes[route_key]
        if credential_id and secret:
            if not self._auth.verify(credential_id, secret):
                return {"error": "unauthorized", "status": 401}
            cred = self._auth.get_credential(credential_id)
            if cred and not set(route["scopes"]).issubset(set(cred.scopes)):
                return {"error": "forbidden", "status": 403}
        elif route["scopes"]:
            return {"error": "unauthorized", "status": 401}
        if self._rate_limiter and not self._rate_limiter.is_allowed(credential_id or "anonymous"):
            return {"error": "rate_limited", "status": 429}
        return route["handler"](**kwargs)
