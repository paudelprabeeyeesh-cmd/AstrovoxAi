"""
Hardened rate limiting backed by Redis (when available) with an
in-process fallback.

Replaces the broken `@limiter.limit` decorators that lacked the
required `request: Request` parameter. The new limiter:

  * Supports sliding window and token bucket algorithms
  * Falls back to an in-process bucket when Redis is unavailable
  * Records every decision in the audit log
  * Returns standard X-RateLimit-* response headers
  * Per-endpoint and per-user keying
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Optional, Tuple

from .security_hardening import AuditLog, get_audit_log
from app.metrics import track_rate_limit


# ---------------------------------------------------------------------------
# Client identity behind a reverse proxy
# ---------------------------------------------------------------------------

def _trust_proxy_headers() -> bool:
    """True only when an operator has said a trusted proxy sets X-Forwarded-For.

    Reading the header unconditionally means any client can claim any IP
    and hop buckets at will, so the trust is opt-in.
    """
    return os.getenv("TRUST_PROXY_HEADERS", "false").strip().lower() in (
        "1", "true", "yes", "on",
    )


def client_identity(request: Any) -> str:
    """Resolve the caller identity used as the rate-limit key.

    Behind nginx, ``request.client.host`` is the proxy's address, which
    collapses every user into a single bucket: one heavy caller then
    rate-limits everyone. The forwarded value is used instead, but only
    when the deployment has declared the proxy trustworthy, so the
    per-user limit is real rather than all-or-nothing.
    """
    if request is None:
        return "unknown"
    if _trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
    client = getattr(request, "client", None)
    return client.host if client else "unknown"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class RateLimitConfig:
    name: str
    requests: int
    window_seconds: float
    scope: str = "user"
    burst: Optional[int] = None


DEFAULT_LIMITS: Dict[str, RateLimitConfig] = {
    "auth_login": RateLimitConfig("auth_login", 5, 60),
    "auth_signup": RateLimitConfig("auth_signup", 3, 3600),
    "auth_password_reset": RateLimitConfig("auth_password_reset", 3, 3600),
    "api_anonymous": RateLimitConfig("api_anonymous", 30, 60),
    "api_authenticated": RateLimitConfig("api_authenticated", 600, 60),
    "api_partner": RateLimitConfig("api_partner", 6000, 60),
    "embeddings": RateLimitConfig("embeddings", 60, 60),
    "chat_completion": RateLimitConfig("chat_completion", 60, 60),
    "code_execution": RateLimitConfig("code_execution", 10, 60),
    "upload": RateLimitConfig("upload", 30, 60),
}


# ---------------------------------------------------------------------------
# Sliding window counter
# ---------------------------------------------------------------------------


class SlidingWindowCounter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: Deque[float] = deque()
        self._lock = threading.Lock()

    def hit(self, amount: int = 1) -> Tuple[bool, int, int]:
        """Record `amount` hits. Returns (allowed, remaining, reset_seconds)."""
        now = time.time()
        with self._lock:
            cutoff = now - self.window
            while self._hits and self._hits[0] < cutoff:
                self._hits.popleft()
            if len(self._hits) + amount > self.limit:
                reset = int(self.window - (now - self._hits[0])) if self._hits else int(self.window)
                return False, 0, max(reset, 0)
            for _ in range(amount):
                self._hits.append(now)
            remaining = self.limit - len(self._hits)
            return True, remaining, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


class TokenBucket:
    """Token bucket for burst protection.

    Refills at a steady rate and allows short bursts up to `burst_capacity`.
    """

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self._last = time.time()
        self._lock = threading.Lock()

    def consume(self, amount: int = 1) -> Tuple[bool, int]:
        with self._lock:
            now = time.time()
            elapsed = now - self._last
            self._last = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            if self.tokens >= amount:
                self.tokens -= amount
                return True, int(self.tokens)
            return False, int(self.tokens)

    def remaining(self) -> int:
        with self._lock:
            return int(self.tokens)


# ---------------------------------------------------------------------------
# In-process limiter (fallback)
# ---------------------------------------------------------------------------


class InProcessLimiter:
    """In-process sliding-window limiter used when Redis is absent.

    The bucket map is bounded. The previous version keyed on
    (policy, identity) and never evicted, so a caller presenting
    unbounded distinct identities grew the dict forever: memory-exhaustion
    DoS of the limiter itself, from the component meant to prevent DoS.
    """

    # Evict when the map exceeds this, keeping at most MAX_BUCKETS entries.
    MAX_BUCKETS = 20_000
    EVICT_BATCH = 2_000

    def __init__(self) -> None:
        self._buckets: DequeTuple = {}
        self._lock = threading.Lock()
        self._configs: Dict[str, RateLimitConfig] = dict(DEFAULT_LIMITS)
        self._evictions = 0

    def configure(self, key: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._configs[key] = config

    def _evict_if_needed(self) -> None:
        """Drop the oldest buckets. Must be called with _lock held."""
        if len(self._buckets) <= self.MAX_BUCKETS:
            return
        # dicts preserve insertion order, so the first entries are the
        # stalest. A window's worth of entries at a time is cheap and
        # amortises the cost of the scan.
        victims = list(self._buckets.items())[: self.EVICT_BATCH]
        for key, _bucket in victims:
            del self._buckets[key]
        self._evictions += len(victims)

    def check(
        self,
        policy: str,
        identity: str,
        *,
        amount: int = 1,
    ) -> Dict[str, Any]:
        config = self._configs.get(policy)
        if config is None:
            return {"allowed": True, "limit": None, "remaining": None}
        bucket_key = f"{policy}:{identity}"
        with self._lock:
            existing = self._buckets.get(bucket_key)
            if existing is None or existing.limit != config.requests:
                self._buckets[bucket_key] = SlidingWindowCounter(
                    config.requests, config.window_seconds
                )
            self._evict_if_needed()
        bucket = self._buckets[bucket_key]
        allowed, remaining, reset = bucket.hit(amount)
        return {
            "allowed": allowed,
            "limit": config.requests,
            "remaining": remaining,
            "reset_seconds": reset,
            "window_seconds": config.window_seconds,
            "policy": policy,
            "identity": identity,
        }

    def bucket_count(self) -> int:
        with self._lock:
            return len(self._buckets)


# ---------------------------------------------------------------------------
# Redis backend (optional)
# ---------------------------------------------------------------------------


class RedisLimiter:
    """Redis-backed sliding window counter.

    Uses a single Redis key per (policy, identity) holding a sorted
    set of timestamps. Trims the set on every hit. Falls back to
    InProcessLimiter when Redis is unreachable.
    """

    def __init__(self, redis_url: str, fallback: InProcessLimiter) -> None:
        self.redis_url = redis_url
        self.fallback = fallback
        self._client = None
        self._connect()

    def _connect(self) -> None:
        if self._client is not None:
            return
        try:
            import redis

            self._client = redis.from_url(
                self.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._client.ping()
        except Exception:
            self._client = None

    def _key(self, policy: str, identity: str) -> str:
        return f"rl:{policy}:{identity}"

    def check(
        self,
        policy: str,
        identity: str,
        *,
        amount: int = 1,
    ) -> Dict[str, Any]:
        if self._client is None:
            return self.fallback.check(policy, identity, amount=amount)
        try:
            key = self._key(policy, identity)
            now = time.time()
            window = DEFAULT_LIMITS.get(
                policy, RateLimitConfig(policy, 60, 60)
            ).window_seconds
            limit = DEFAULT_LIMITS.get(
                policy, RateLimitConfig(policy, 60, 60)
            ).requests
            cutoff = now - window
            with self._client.pipeline() as pipe:
                pipe.zremrangebyscore(key, 0, cutoff)
                pipe.zcard(key)
                pipe.expire(key, int(window) + 1)
                _, count, _ = pipe.execute()
            if count + amount > limit:
                return {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_seconds": int(window),
                    "policy": policy,
                    "identity": identity,
                }
            member = f"{now}:{amount}:{secrets_token(8)}"
            with self._client.pipeline() as pipe:
                pipe.zadd(key, {member: now})
                pipe.expire(key, int(window) + 1)
                pipe.execute()
            return {
                "allowed": True,
                "limit": limit,
                "remaining": max(0, limit - int(count) - amount),
                "reset_seconds": 0,
                "policy": policy,
                "identity": identity,
            }
        except Exception:
            return self.fallback.check(policy, identity, amount=amount)


def secrets_token(length: int = 16) -> str:
    import secrets as _s

    return _s.token_hex(length // 2)


# ---------------------------------------------------------------------------
# Global limiter
# ---------------------------------------------------------------------------


_GLOBAL_LIMITER: Optional["RateLimiter"] = None


class RateLimiter:
    """Top-level facade used by route dependencies."""

    def __init__(self) -> None:
        self._inprocess = InProcessLimiter()
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            self._redis: Optional[RedisLimiter] = RedisLimiter(
                redis_url, self._inprocess
            )
        else:
            self._redis = None
        self._audit: AuditLog = get_audit_log()
        self._burst_buckets: Dict[str, TokenBucket] = {}
        # Bound the burst-bucket map too, for the same reason as
        # InProcessLimiter: an unbounded identity set grew it forever.
        self._MAX_BURST_BUCKETS = 20_000

    def _get_burst_bucket(self, policy: str, identity: str) -> Optional[TokenBucket]:
        config = DEFAULT_LIMITS.get(policy)
        if config is None or config.burst is None:
            return None
        key = f"{policy}:{identity}"
        bucket = self._burst_buckets.get(key)
        if bucket is None:
            if len(self._burst_buckets) >= self._MAX_BURST_BUCKETS:
                # Insertion-ordered; drop the oldest batch rather than a
                # random one, so hot identities survive.
                for old in list(self._burst_buckets)[:2000]:
                    self._burst_buckets.pop(old, None)
            refill_rate = config.requests / config.window_seconds
            bucket = TokenBucket(config.burst, refill_rate)
            self._burst_buckets[key] = bucket
        return bucket

    def configure(self, key: str, config: RateLimitConfig) -> None:
        self._inprocess.configure(key, config)

    def check(
        self,
        policy: str,
        identity: str,
        *,
        amount: int = 1,
    ) -> Dict[str, Any]:
        burst = self._get_burst_bucket(policy, identity)
        if burst is not None:
            allowed, remaining = burst.consume(amount)
            if not allowed:
                result = {
                    "allowed": False,
                    "limit": DEFAULT_LIMITS.get(policy, RateLimitConfig(policy, 60, 60)).requests,
                    "remaining": 0,
                    "reset_seconds": 0,
                    "policy": policy,
                    "identity": identity,
                }
                self._audit.record(
                    actor=identity or "anonymous",
                    action="rate_limit_exceeded",
                    target=policy,
                    outcome="denied",
                    metadata={"policy": policy, "amount": amount, "burst": True},
                )
                track_rate_limit(policy, identity or "anonymous", False, 0)
                return result
        if self._redis is not None:
            result = self._redis.check(policy, identity, amount=amount)
        else:
            result = self._inprocess.check(policy, identity, amount=amount)
        if not result.get("allowed", True):
            self._audit.record(
                actor=identity or "anonymous",
                action="rate_limit_exceeded",
                target=policy,
                outcome="denied",
                metadata={
                    "policy": policy,
                    "amount": amount,
                    "limit": result.get("limit"),
                },
            )
        track_rate_limit(policy, identity or "anonymous", result.get("allowed", True), result.get("remaining", 0))
        return result


def get_rate_limiter() -> RateLimiter:
    global _GLOBAL_LIMITER
    if _GLOBAL_LIMITER is None:
        _GLOBAL_LIMITER = RateLimiter()
    return _GLOBAL_LIMITER


# ---------------------------------------------------------------------------
# FastAPI middleware
# ---------------------------------------------------------------------------

from fastapi import Request
from fastapi.responses import JSONResponse


async def rate_limit_middleware(request: Request, call_next):
    limiter = get_rate_limiter()
    # Keyed on the real caller, not the proxy's address, so one heavy
    # caller cannot consume everyone's budget.
    client_ip = client_identity(request)
    result = limiter.check("api_anonymous", client_ip)
    if not result.get("allowed", True):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={
                "X-RateLimit-Limit": str(result.get("limit") or ""),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(result.get("reset_seconds") or 60),
            },
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(result.get("limit") or "")
    response.headers["X-RateLimit-Remaining"] = str(result.get("remaining") or 0)
    return response


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


from fastapi import HTTPException, Request


def rate_limit(policy: str, *, amount: int = 1):
    """Create a FastAPI dependency that enforces the named rate limit."""

    async def _dep(
        request: Request,
        principal=None,
    ) -> Dict[str, Any]:
        from ..iam import get_current_principal

        if principal is None:
            principal = await get_current_principal(request=request)
        if getattr(principal, "role", "") == "anonymous":
            identity = client_identity(request)
        else:
            identity = principal.id
        result = get_rate_limiter().check(policy, identity, amount=amount)
        if not result.get("allowed", True):
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(result.get("limit") or ""),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(result.get("reset_seconds") or 60),
                },
            )
        return result

    return _dep
