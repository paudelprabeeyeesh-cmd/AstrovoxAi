"""Idempotency keys for safe retries."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
import redis
import json


class IdempotencyManager:
    _redis: Optional[redis.Redis] = None
    _prefix = "idempotency:"
    _ttl = 86400

    @classmethod
    def initialize(cls, redis_url: str = "redis://localhost:6379/0") -> None:
        cls._redis = redis.from_url(redis_url, decode_responses=True)

    @classmethod
    def store_response(cls, key: str, response_data: Dict[str, Any], status_code: int) -> None:
        if not cls._redis:
            cls.initialize()
        payload = {
            "status_code": status_code,
            "response": response_data,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }
        cls._redis.setex(f"{cls._prefix}{key}", cls._ttl, json.dumps(payload))

    @classmethod
    def get_response(cls, key: str) -> Optional[Dict[str, Any]]:
        if not cls._redis:
            cls.initialize()
        data = cls._redis.get(f"{cls._prefix}{key}")
        if data:
            return json.loads(data)
        return None

    @classmethod
    def has_response(cls, key: str) -> bool:
        if not cls._redis:
            cls.initialize()
        return cls._redis.exists(f"{cls._prefix}{key}") > 0

    @classmethod
    def delete_key(cls, key: str) -> None:
        if not cls._redis:
            cls.initialize()
        cls._redis.delete(f"{cls._prefix}{key}")
