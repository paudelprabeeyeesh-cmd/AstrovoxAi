"""
API Gateway with rate limiting, circuit breaking, and request routing.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    key: str
    max_requests: int
    window_seconds: int
    burst: int = 0


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class SlidingWindowCounter:
    """Sliding window counter rate limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()

    def allow(self) -> bool:
        now = time.time()
        while self.requests and self.requests[0] < now - self.window_seconds:
            self.requests.popleft()
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False


class APIGateway:
    """API Gateway with rate limiting and routing."""

    def __init__(self):
        self.routes: Dict[str, Callable] = {}
        self.rate_limiters: Dict[str, SlidingWindowCounter] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}
        self.request_log: List[dict] = []
        self.circuit_breakers: Dict[str, dict] = {}

    def register_route(self, path: str, handler: Callable, methods: List[str] = None):
        self.routes[path] = {"handler": handler, "methods": methods or ["GET", "POST"]}

    def add_rate_limit(self, key: str, max_requests: int, window_seconds: int):
        self.rate_limiters[key] = SlidingWindowCounter(max_requests, window_seconds)

    def add_token_bucket(self, key: str, capacity: int, refill_rate: float):
        self.token_buckets[key] = TokenBucket(capacity, refill_rate)

    def is_rate_limited(self, key: str) -> bool:
        if key in self.rate_limiters:
            return not self.rate_limiters[key].allow()
        if key in self.token_buckets:
            return not self.token_buckets[key].consume()
        return False

    def route_request(self, path: str, method: str, user_id: str, payload: dict) -> dict:
        route_key = f"{method}:{path}"
        user_key = f"user:{user_id}"
        if self.is_rate_limited(user_key):
            return {"status": 429, "error": "Rate limit exceeded", "retry_after": 60}
        if route_key not in self.routes:
            return {"status": 404, "error": f"Route {route_key} not found"}
        route = self.routes[route_key]
        if method not in route["methods"]:
            return {"status": 405, "error": f"Method {method} not allowed"}
        try:
            start = time.time()
            result = route["handler"](payload)
            latency = time.time() - start
            self.request_log.append({"path": path, "method": method, "user_id": user_id, "status": "success", "latency_ms": latency * 1000})
            return {"status": 200, "data": result, "latency_ms": round(latency * 1000, 2)}
        except Exception as e:
            logger.error(f"Route {route_key} failed: {e}")
            return {"status": 500, "error": str(e)}

    def get_metrics(self) -> dict:
        total = len(self.request_log)
        errors = sum(1 for r in self.request_log if r.get("status") == "error")
        return {
            "total_requests": total,
            "errors": errors,
            "success_rate": round((total - errors) / max(total, 1) * 100, 1),
            "registered_routes": len(self.routes),
        }
