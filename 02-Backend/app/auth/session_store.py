"""Session store with Redis backing."""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
import json
import redis


class SessionStore:
    _redis: Optional[redis.Redis] = None
    _prefix = "session:"
    _ttl_seconds = 86400

    @classmethod
    def initialize(cls, redis_url: str = "redis://localhost:6379/0") -> None:
        cls._redis = redis.from_url(redis_url, decode_responses=True)

    @classmethod
    def create_session(cls, user_id: str, data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        if not cls._redis:
            cls.initialize()
        session_id = secrets.token_urlsafe(32)
        data["user_id"] = user_id
        data["created_at"] = datetime.now(timezone.utc).isoformat()
        cls._redis.setex(
            f"{cls._prefix}{session_id}",
            ttl or cls._ttl_seconds,
            json.dumps(data),
        )
        return session_id

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        if not cls._redis:
            cls.initialize()
        data = cls._redis.get(f"{cls._prefix}{session_id}")
        if data:
            return json.loads(data)
        return None

    @classmethod
    def update_session(cls, session_id: str, data: Dict[str, Any]) -> bool:
        if not cls._redis:
            cls.initialize()
        existing = cls.get_session(session_id)
        if not existing:
            return False
        existing.update(data)
        cls._redis.setex(
            f"{cls._prefix}{session_id}",
            cls._ttl_seconds,
            json.dumps(existing),
        )
        return True

    @classmethod
    def delete_session(cls, session_id: str) -> None:
        if not cls._redis:
            cls.initialize()
        cls._redis.delete(f"{cls._prefix}{session_id}")

    @classmethod
    def extend_session(cls, session_id: str, ttl: Optional[int] = None) -> bool:
        if not cls._redis:
            cls.initialize()
        if cls._redis.exists(f"{cls._prefix}{session_id}"):
            cls._redis.expire(f"{cls._prefix}{session_id}", ttl or cls._ttl_seconds)
            return True
        return False
