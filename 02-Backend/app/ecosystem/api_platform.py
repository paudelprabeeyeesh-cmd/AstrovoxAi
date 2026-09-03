"""Public API platform: API key management, OAuth 2.0, rate limiting, analytics.

Supports:
- API key issuance with hashed secrets
- OAuth 2.0 (authorization code, client credentials, refresh token)
- Rate limiting policies and sliding window
- API analytics
- Standardized error envelope
- Webhook signature helpers (HMAC SHA-256)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Tuple


class ApiErrorCode(str, Enum):
    BAD_REQUEST = "bad_request"
    UNAUTHENTICATED = "unauthenticated"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INTERNAL = "internal_error"
    UPSTREAM = "upstream_error"
    DEPRECATED = "deprecated"


@dataclass
class ApiError:
    code: ApiErrorCode
    message: str
    status: int
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "status": self.status,
                "details": self.details or {},
                "request_id": self.request_id,
            }
        }


def api_error(
    code: ApiErrorCode,
    message: str,
    status: int,
    request_id: Optional[str] = None,
    **details: Any,
) -> Dict[str, Any]:
    return ApiError(code, message, status, details or None, request_id).to_dict()


class RateLimitScope(str, Enum):
    GLOBAL = "global"
    PER_KEY = "per_key"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"


@dataclass
class RateLimitPolicy:
    name: str
    scope: RateLimitScope
    limit: int
    window_seconds: int
    burst: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scope": self.scope.value,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "burst": self.burst,
        }


DEFAULT_POLICIES: List[RateLimitPolicy] = [
    RateLimitPolicy("public", RateLimitScope.PER_KEY, 60, 60, burst=120),
    RateLimitPolicy("authenticated", RateLimitScope.PER_KEY, 600, 60, burst=1200),
    RateLimitPolicy("partner", RateLimitScope.PER_KEY, 6000, 60, burst=12000),
    RateLimitPolicy("chat_completions", RateLimitScope.PER_ENDPOINT, 30, 60, burst=60),
    RateLimitPolicy("webhooks_publish", RateLimitScope.PER_KEY, 300, 60, burst=600),
]


class TokenBucket:
    """Sliding-window rate limiter bucket."""

    def __init__(self, limit: int, window: int) -> None:
        self.limit = limit
        self.window = window
        self._hits: Deque[float] = deque()

    def consume(self, amount: int = 1) -> Tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window
        while self._hits and self._hits[0] < cutoff:
            self._hits.popleft()
        if len(self._hits) + amount > self.limit:
            retry = int(self.window - (now - self._hits[0])) if self._hits else self.window
            return False, max(retry, 1)
        for _ in range(amount):
            self._hits.append(now)
        return True, 0

    def remaining(self) -> int:
        now = time.time()
        cutoff = now - self.window
        while self._hits and self._hits[0] < cutoff:
            self._hits.popleft()
        return max(self.limit - len(self._hits), 0)


class RateLimiter:
    def __init__(self, policies: Optional[List[RateLimitPolicy]] = None) -> None:
        self.policies: Dict[str, RateLimitPolicy] = {
            p.name: p for p in (policies or DEFAULT_POLICIES)
        }
        self._buckets: Dict[Tuple[str, str], TokenBucket] = {}

    def _get_bucket(self, policy_name: str, key: str) -> TokenBucket:
        bkey = (policy_name, key)
        bucket = self._buckets.get(bkey)
        if bucket is None:
            policy = self.policies[policy_name]
            bucket = TokenBucket(policy.limit, policy.window_seconds)
            self._buckets[bkey] = bucket
        return bucket

    def check(self, policy_name: str, key: str, amount: int = 1) -> Dict[str, Any]:
        policy = self.policies.get(policy_name)
        if policy is None:
            return {"allowed": True, "policy": policy_name, "remaining": -1}
        bucket = self._get_bucket(policy_name, key)
        allowed, retry = bucket.consume(amount)
        return {
            "allowed": allowed,
            "policy": policy_name,
            "remaining": bucket.remaining() if allowed else 0,
            "retry_after": retry,
            "limit": policy.limit,
            "window_seconds": policy.window_seconds,
        }

    def add_policy(self, policy: RateLimitPolicy) -> None:
        self.policies[policy.name] = policy

    def status(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.policies.values()]


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


@dataclass
class ApiKey:
    id: str
    label: str
    owner_id: str
    key_hash: str
    secret_hash: str
    prefix: str
    scopes: List[str]
    tier: str = "authenticated"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_used: Optional[str] = None
    revoked: bool = False
    description: str = ""

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "label": self.label,
            "owner_id": self.owner_id,
            "prefix": self.prefix,
            "scopes": self.scopes,
            "tier": self.tier,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "revoked": self.revoked,
            "description": self.description,
        }
        if include_secrets:
            data["key_hash"] = self.key_hash
        return data


from datetime import datetime, timezone  # noqa: E402


class ApiKeyStore:
    """In-memory API key store with hashed secrets."""

    SALT = "astrovox-api-v1"

    def __init__(self) -> None:
        self._keys: Dict[str, ApiKey] = {}
        self._by_prefix: Dict[str, str] = {}

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(f"{ApiKeyStore.SALT}:{value}".encode("utf-8")).hexdigest()

    @staticmethod
    def _generate(prefix: str = "ak") -> str:
        return f"{prefix}_{secrets.token_urlsafe(32)}"

    def issue(
        self,
        owner_id: str,
        label: str,
        scopes: Iterable[str],
        tier: str = "authenticated",
        description: str = "",
    ) -> Tuple[ApiKey, str, str]:
        import uuid as _uuid
        key_id = f"key_{_uuid.uuid4().hex[:12]}"
        api_key = self._generate("ak")
        api_secret = self._generate("sk")
        record = ApiKey(
            id=key_id,
            label=label,
            owner_id=owner_id,
            key_hash=self._hash(api_key),
            secret_hash=self._hash(api_secret),
            prefix=api_key[:10],
            scopes=list(scopes),
            tier=tier,
            description=description,
        )
        self._keys[key_id] = record
        self._by_prefix[api_key[:10]] = key_id
        return record, api_key, api_secret

    def verify(self, api_key: str, api_secret: str) -> Optional[ApiKey]:
        if not api_key or not api_secret:
            return None
        key_id = self._by_prefix.get(api_key[:10])
        if not key_id:
            return None
        record = self._keys.get(key_id)
        if not record or record.revoked:
            return None
        if not hmac.compare_digest(record.key_hash, self._hash(api_key)):
            return None
        if not hmac.compare_digest(record.secret_hash, self._hash(api_secret)):
            return None
        record.last_used = datetime.now(timezone.utc).isoformat()
        return record

    def revoke(self, key_id: str) -> Optional[ApiKey]:
        record = self._keys.get(key_id)
        if record is None:
            return None
        record.revoked = True
        return record

    def list(self, owner_id: Optional[str] = None) -> List[ApiKey]:
        if owner_id is None:
            return list(self._keys.values())
        return [k for k in self._keys.values() if k.owner_id == owner_id]

    def get(self, key_id: str) -> Optional[ApiKey]:
        return self._keys.get(key_id)


# ---------------------------------------------------------------------------
# OAuth 2.0
# ---------------------------------------------------------------------------


@dataclass
class OAuthClient:
    id: str
    secret_hash: str
    name: str
    redirect_uris: List[str]
    scopes: List[str] = field(default_factory=list)
    confidential: bool = True


@dataclass
class OAuthToken:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str = ""
    client_id: str = ""
    user_id: Optional[str] = None
    issued_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.issued_at >= self.expires_in


class OAuthServer:
    """Lightweight OAuth 2.0 server supporting the standard flows."""

    AUTH_CODE_TTL = 300
    ACCESS_TTL = 3600
    REFRESH_TTL = 60 * 60 * 24 * 30

    def __init__(self) -> None:
        self.clients: Dict[str, OAuthClient] = {}
        self._codes: Dict[str, Dict[str, Any]] = {}
        self._tokens: Dict[str, OAuthToken] = {}

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def register_client(
        self,
        name: str,
        redirect_uris: List[str],
        scopes: Optional[List[str]] = None,
    ) -> Tuple[OAuthClient, str]:
        import uuid as _uuid
        client_id = f"cli_{_uuid.uuid4().hex[:10]}"
        secret = secrets.token_urlsafe(32)
        client = OAuthClient(
            id=client_id,
            secret_hash=self._hash(secret),
            name=name,
            redirect_uris=list(redirect_uris),
            scopes=list(scopes or []),
        )
        self.clients[client_id] = client
        return client, secret

    def authenticate_client(
        self, client_id: str, client_secret: str
    ) -> Optional[OAuthClient]:
        client = self.clients.get(client_id)
        if not client:
            return None
        return client if hmac.compare_digest(client.secret_hash, self._hash(client_secret)) else None

    def authorization_code(
        self,
        client_id: str,
        user_id: str,
        redirect_uri: str,
        scope: str,
        state: Optional[str] = None,
    ) -> str:
        code = secrets.token_urlsafe(32)
        self._codes[code] = {
            "client_id": client_id,
            "user_id": user_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
            "expires_at": time.time() + self.AUTH_CODE_TTL,
        }
        return code

    def exchange_code(
        self, code: str, client_id: str, redirect_uri: str
    ) -> Optional[OAuthToken]:
        data = self._codes.pop(code, None)
        if not data or data["expires_at"] < time.time():
            return None
        if data["client_id"] != client_id or data["redirect_uri"] != redirect_uri:
            return None
        return self._issue_token(client_id, data["user_id"], data["scope"])

    def client_credentials(self, client_id: str, scope: str) -> Optional[OAuthToken]:
        client = self.clients.get(client_id)
        if not client:
            return None
        return self._issue_token(client_id, None, scope)

    def refresh(self, refresh_token: str) -> Optional[OAuthToken]:
        token = self._tokens.get(refresh_token)
        if not token or token.is_expired():
            return None
        return self._issue_token(token.client_id, token.user_id, token.scope)

    def introspect(self, access_token: str) -> Optional[Dict[str, Any]]:
        token = self._tokens.get(access_token)
        if not token or token.is_expired():
            return None
        return {
            "active": True,
            "client_id": token.client_id,
            "user_id": token.user_id,
            "scope": token.scope,
            "exp": int(token.issued_at + token.expires_in),
            "token_type": token.token_type,
        }

    def _issue_token(self, client_id: str, user_id: Optional[str], scope: str) -> OAuthToken:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        token = OAuthToken(
            access_token=access,
            token_type="Bearer",
            expires_in=self.ACCESS_TTL,
            refresh_token=refresh,
            scope=scope,
            client_id=client_id,
            user_id=user_id,
        )
        self._tokens[access] = token
        self._tokens[refresh] = OAuthToken(
            access_token=refresh,
            token_type="Bearer",
            expires_in=self.REFRESH_TTL,
            refresh_token=None,
            scope=scope,
            client_id=client_id,
            user_id=user_id,
            issued_at=token.issued_at,
        )
        return token


# ---------------------------------------------------------------------------
# Webhook signature helpers
# ---------------------------------------------------------------------------


def sign_payload(payload: bytes, secret: str, timestamp: Optional[int] = None) -> str:
    ts = timestamp or int(time.time())
    mac = hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + payload,
        hashlib.sha256,
    ).hexdigest()
    return f"t={ts},v1={mac}"


def verify_signature(
    payload: bytes,
    signature: str,
    secret: str,
    max_age_seconds: int = 300,
) -> bool:
    if not signature:
        return False
    parts = dict(p.split("=", 1) for p in signature.split(",") if "=" in p)
    ts_raw = parts.get("t")
    sig = parts.get("v1")
    if not ts_raw or not sig:
        return False
    try:
        ts = int(ts_raw)
    except ValueError:
        return False
    if abs(time.time() - ts) > max_age_seconds:
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig)


# ---------------------------------------------------------------------------
# API analytics
# ---------------------------------------------------------------------------


@dataclass
class ApiCall:
    timestamp: float
    endpoint: str
    method: str
    status: int
    latency_ms: float
    key_id: Optional[str] = None
    user_id: Optional[str] = None
    error_code: Optional[str] = None


class ApiAnalytics:
    def __init__(self, max_samples: int = 5000) -> None:
        self._calls: Deque[ApiCall] = deque(maxlen=max_samples)
        self._by_endpoint: Dict[str, List[ApiCall]] = defaultdict(list)
        self._by_key: Dict[str, List[ApiCall]] = defaultdict(list)
        self._errors: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, List[float]] = defaultdict(list)

    def record(self, call: ApiCall) -> None:
        self._calls.append(call)
        self._by_endpoint[f"{call.method} {call.endpoint}"].append(call)
        if call.key_id:
            self._by_key[call.key_id].append(call)
        if call.error_code:
            self._errors[call.error_code] += 1
        self._latencies[f"{call.method} {call.endpoint}"].append(call.latency_ms)

    def summary(self) -> Dict[str, Any]:
        total = len(self._calls)
        errors = sum(1 for c in self._calls if c.status >= 400)
        avg_latency = (
            sum(c.latency_ms for c in self._calls) / total if total else 0.0
        )
        return {
            "total_calls": total,
            "error_rate": (errors / total) if total else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "errors_by_code": dict(self._errors),
            "calls_by_key": {k: len(v) for k, v in self._by_key.items()},
            "calls_by_endpoint": {k: len(v) for k, v in self._by_endpoint.items()},
        }

    def endpoint_perf(self, endpoint: str) -> Dict[str, Any]:
        samples = self._latencies.get(endpoint, [])
        if not samples:
            return {"endpoint": endpoint, "count": 0}
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        p50 = sorted_samples[n // 2]
        p95 = sorted_samples[min(n - 1, int(n * 0.95))]
        return {
            "endpoint": endpoint,
            "count": n,
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "max_ms": round(max(samples), 2),
        }


# ---------------------------------------------------------------------------
# Endpoint registry
# ---------------------------------------------------------------------------


@dataclass
class ApiEndpoint:
    name: str
    method: str
    path: str
    handler: Callable[..., Any]
    description: str
    scopes: List[str] = field(default_factory=list)
    rate_limit: str = "authenticated"
    version: str = "v1"
    examples: Dict[str, Any] = field(default_factory=dict)
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "method": self.method,
            "path": self.path,
            "version": self.version,
            "description": self.description,
            "scopes": self.scopes,
            "rate_limit": self.rate_limit,
            "examples": self.examples,
            "request_schema": self.request_schema,
            "response_schema": self.response_schema,
        }


class ApiRegistry:
    def __init__(self) -> None:
        self.endpoints: Dict[str, ApiEndpoint] = {}

    def register(self, endpoint: ApiEndpoint) -> None:
        self.endpoints[endpoint.name] = endpoint

    def list(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        eps = self.endpoints.values()
        if version:
            eps = [e for e in eps if e.version == version]
        return [e.to_dict() for e in eps]

    def get(self, name: str) -> Optional[ApiEndpoint]:
        return self.endpoints.get(name)


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


_GLOBAL_KEY_STORE: Optional[ApiKeyStore] = None
_GLOBAL_OAUTH: Optional[OAuthServer] = None
_GLOBAL_LIMITER: Optional[RateLimiter] = None
_GLOBAL_ANALYTICS: Optional[ApiAnalytics] = None
_GLOBAL_REGISTRY: Optional[ApiRegistry] = None


def get_key_store() -> ApiKeyStore:
    global _GLOBAL_KEY_STORE
    if _GLOBAL_KEY_STORE is None:
        _GLOBAL_KEY_STORE = ApiKeyStore()
    return _GLOBAL_KEY_STORE


def get_oauth_server() -> OAuthServer:
    global _GLOBAL_OAUTH
    if _GLOBAL_OAUTH is None:
        _GLOBAL_OAUTH = OAuthServer()
    return _GLOBAL_OAUTH


def get_rate_limiter() -> RateLimiter:
    global _GLOBAL_LIMITER
    if _GLOBAL_LIMITER is None:
        _GLOBAL_LIMITER = RateLimiter()
    return _GLOBAL_LIMITER


def get_api_analytics() -> ApiAnalytics:
    global _GLOBAL_ANALYTICS
    if _GLOBAL_ANALYTICS is None:
        _GLOBAL_ANALYTICS = ApiAnalytics()
    return _GLOBAL_ANALYTICS


def get_api_registry() -> ApiRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ApiRegistry()
    return _GLOBAL_REGISTRY