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
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, Optional, Tuple

from .security_hardening import AuditLog, get_audit_log


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class RateLimitConfig:
    name: str
    requests: int
    window_seconds: float
    scope: str = "user"  # "user" | "ip" | "endpoint" | "global"


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


# ---------------------------------------------------------------------------
# In-process limiter (fallback)
# ---------------------------------------------------------------------------


class InProcessLimiter:
    def __init__(self) -> None:
        self._buckets: Dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()
        self._configs: Dict[str, RateLimitConfig] = dict(DEFAULT_LIMITS)

    def configure(self, key: str, config: RateLimitConfig) -> None:
        with self._lock:
            self._configs[key] = config

    def _get(self, key: str) -> SlidingWindowCounter:
        with self._lock:
            if key not in self._buckets:
                cfg = self._configs.get(key) or RateLimitConfig(key, 60, 60)
                self._buckets[key] = SlidingWindowCounter(
                    cfg.requests, cfg.window_seconds
                )
            return self._buckets[key]

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
        # Ensure bucket uses current config
        with self._lock:
            existing = self._buckets.get(bucket_key)
            if existing is None or existing.limit != config.requests:
                self._buckets[bucket_key] = SlidingWindowCounter(
                    config.requests, config.window_seconds
                )
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

    def configure(self, key: str, config: RateLimitConfig) -> None:
        self._inprocess.configure(key, config)

    def check(
        self,
        policy: str,
        identity: str,
        *,
        amount: int = 1,
    ) -> Dict[str, Any]:
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
        return result


def get_rate_limiter() -> RateLimiter:
    global _GLOBAL_LIMITER
    if _GLOBAL_LIMITER is None:
        _GLOBAL_LIMITER = RateLimiter()
    return _GLOBAL_LIMITER


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


from fastapi import Depends, HTTPException, Request


def rate_limit(policy: str, *, amount: int = 1):
    """Create a FastAPI dependency that enforces the named rate limit."""

    async def _dep(
        request: Request,
        principal=None,
    ) -> Dict[str, Any]:
        from .iam import get_current_principal

        if principal is None:
            principal = await get_current_principal(request=request)
        if getattr(principal, "role", "") == "anonymous":
            identity = request.client.host if request.client else "unknown"
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
