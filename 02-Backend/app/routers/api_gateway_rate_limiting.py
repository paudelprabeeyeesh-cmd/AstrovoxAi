import logging
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import require_verified_email, require_admin
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["api-gateway"])


class TokenBucket:
    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = {}
        self.last_refill = {}

    def _refill(self, key: str):
        import time
        now = time.time()
        if key not in self.last_refill:
            self.last_refill[key] = now
            self.tokens[key] = self.capacity
        delta = now - self.last_refill[key]
        added = delta * self.refill_rate
        self.tokens[key] = min(self.capacity, self.tokens[key] + added)
        self.last_refill[key] = now

    def consume(self, key: str, amount: int = 1) -> bool:
        self._refill(key)
        if self.tokens.get(key, 0) >= amount:
            self.tokens[key] -= amount
            return True
        return False


_bucket = TokenBucket(capacity=100, refill_rate=10.0)


@router.post("/gateway/rate-limit/test")
async def test_rate_limit(req: dict, user_id: str = Depends(require_verified_email)):
    requests = req.get("requests", 50)
    results = []
    for i in range(requests):
        allowed = _bucket.consume(user_id)
        results.append({"request": i + 1, "allowed": allowed})
    return {
        "user_id": user_id,
        "total_requests": requests,
        "allowed": sum(1 for r in results if r["allowed"]),
        "denied": sum(1 for r in results if not r["allowed"]),
        "results": results[:20],
    }


@router.get("/gateway/region-routing")
async def get_region_routing(user_id: str = Depends(require_verified_email)):
    import random
    regions = {
        "us-east": {"lat": 40.71, "lon": -74.00, "capacity": 80, "available": random.randint(50, 80)},
        "us-west": {"lat": 37.77, "lon": -122.41, "capacity": 80, "available": random.randint(50, 80)},
        "eu-west": {"lat": 51.50, "lon": -0.12, "capacity": 80, "available": random.randint(50, 80)},
        "ap-southeast": {"lat": 1.35, "lon": 103.81, "capacity": 80, "available": random.randint(50, 80)},
    }
    optimal_region = min(regions.keys(), key=lambda r: regions[r]["available"])
    return {
        "regions": regions,
        "recommended_region": optimal_region,
        "estimated_latency_ms": {"us-east": 12, "us-west": 45, "eu-west": 85, "ap-southeast": 180}[optimal_region],
    }


@router.post("/gateway/global-rate-limit")
async def global_rate_limit_check(request: Request, user_id: str = Depends(require_admin)):
    x_forwarded_for = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    with get_db() as conn:
        window_start = (datetime.now(timezone.utc).timestamp() - 60)
        recent = conn.execute(
            "SELECT COUNT(*) as count FROM api_requests WHERE timestamp > ? AND user_id != ?",
            (window_start, "admin"),
        ).fetchone()
    limit = 1000
    current = recent["count"] if recent else 0
    return {
        "ip": x_forwarded_for,
        "requests_last_minute": current,
        "limit": limit,
        "remaining": max(0, limit - current),
        "status": "ok" if current < limit else "rate_limited",
    }


@router.post("/gateway/log-request")
async def log_request(req: dict, user_id: str = Depends(require_verified_email)):
    request_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "endpoint": req.get("endpoint", ""),
        "method": req.get("method", "GET"),
        "status_code": req.get("status_code", 200),
        "response_time_ms": req.get("response_time_ms", 0),
        "tokens_used": req.get("tokens_used", 0),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_requests (id, user_id, endpoint, method, status_code, response_time_ms, tokens_used, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (request_data["id"], request_data["user_id"], request_data["endpoint"], request_data["method"], request_data["status_code"], request_data["response_time_ms"], request_data["tokens_used"], request_data["timestamp"]),
        )
        conn.commit()
    return {"logged": True, "request_id": request_data["id"]}
