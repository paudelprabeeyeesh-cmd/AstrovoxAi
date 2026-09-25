import os
import json
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import redis

from repositories.database.client import get_db

logger = logging.getLogger(__name__)


class MemoryTier(str):
    WORKING = "working"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ARCHIVE = "archive"


class MemoryRecord:
    def __init__(self, id: str, user_id: str, key: str, value: str, tier: str, metadata: dict[str, Any] | None = None, created_at: str | None = None):
        self.id = id
        self.user_id = user_id
        self.key = key
        self.value = value
        self.tier = tier
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()


class HierarchicalMemory:
    def __init__(self):
        self._redis: redis.Redis | None = None

    def _get_redis(self) -> redis.Redis | None:
        if self._redis is None:
            try:
                self._redis = redis.Redis.from_url(
                    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    decode_responses=True,
                )
                self._redis.exists("test")
            except Exception:
                self._redis = None
        return self._redis

    def store(self, user_id: str, key: str, value: str, metadata: dict[str, Any] | None = None) -> MemoryRecord:
        record = MemoryRecord(str(uuid.uuid4()), user_id, key, value, MemoryTier.WORKING, metadata)
        self._store_in_tier(record)
        return record

    def promote_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.tier == MemoryTier.WORKING:
            memory.tier = MemoryTier.SHORT_TERM
        elif memory.tier == MemoryTier.SHORT_TERM:
            memory.tier = MemoryTier.LONG_TERM
        elif memory.tier == MemoryTier.LONG_TERM:
            memory.tier = MemoryTier.ARCHIVE
        self._store_in_tier(memory)
        return memory

    def demote_memory(self, memory: MemoryRecord) -> MemoryRecord:
        if memory.tier == MemoryTier.ARCHIVE:
            memory.tier = MemoryTier.LONG_TERM
        elif memory.tier == MemoryTier.LONG_TERM:
            memory.tier = MemoryTier.SHORT_TERM
        elif memory.tier == MemoryTier.SHORT_TERM:
            memory.tier = MemoryTier.WORKING
        self._store_in_tier(memory)
        return memory

    def get_memories(self, user_id: str, tier: str | None = None, limit: int = 100) -> list[MemoryRecord]:
        if tier == MemoryTier.WORKING:
            return self._get_working_memories(user_id, limit)
        if tier == MemoryTier.SHORT_TERM:
            return self._get_short_term_memories(user_id, limit)
        if tier == MemoryTier.LONG_TERM:
            return self._get_long_term_memories(user_id, limit)
        if tier == MemoryTier.ARCHIVE:
            return self._get_archive_memories(user_id, limit)
        combined: list[MemoryRecord] = []
        for t in [MemoryTier.WORKING, MemoryTier.SHORT_TERM, MemoryTier.LONG_TERM, MemoryTier.ARCHIVE]:
            combined.extend(self.get_memories(user_id, t, limit))
        return combined[:limit]

    def _store_in_tier(self, memory: MemoryRecord) -> None:
        if memory.tier == MemoryTier.WORKING:
            self._store_working(memory)
        elif memory.tier == MemoryTier.SHORT_TERM:
            self._store_short_term(memory)
        elif memory.tier == MemoryTier.LONG_TERM:
            self._store_long_term(memory)
        elif memory.tier == MemoryTier.ARCHIVE:
            self._store_archive(memory)

    def _store_working(self, memory: MemoryRecord) -> None:
        client = self._get_redis()
        if client:
            try:
                client.setex(
                    f"memory:working:{memory.user_id}:{memory.key}",
                    3600,
                    json.dumps({
                        "id": memory.id,
                        "key": memory.key,
                        "value": memory.value,
                        "tier": memory.tier,
                        "metadata": memory.metadata,
                        "created_at": memory.created_at,
                    }),
                )
            except Exception:
                pass

    def _store_short_term(self, memory: MemoryRecord) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (id, user_id, key, value, memory_type, importance_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (memory.id, memory.user_id, memory.key, memory.value, memory.tier, 0.5, memory.created_at),
            )
            conn.commit()

    def _store_long_term(self, memory: MemoryRecord) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (id, user_id, key, value, memory_type, importance_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (memory.id, memory.user_id, memory.key, memory.value, memory.tier, 0.9, memory.created_at),
            )
            conn.commit()

    def _store_archive(self, memory: MemoryRecord) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memories (id, user_id, key, value, memory_type, importance_score, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (memory.id, memory.user_id, memory.key, memory.value, memory.tier, 1.0, memory.created_at),
            )
            conn.commit()

    def _get_working_memories(self, user_id: str, limit: int) -> list[MemoryRecord]:
        client = self._get_redis()
        if not client:
            return []
        pattern = f"memory:working:{user_id}:*"
        keys = client.keys(pattern)[:limit]
        records = []
        for key in keys:
            try:
                data = json.loads(client.get(key) or "{}")
                records.append(MemoryRecord(
                    id=data.get("id", ""),
                    user_id=user_id,
                    key=data.get("key", ""),
                    value=data.get("value", ""),
                    tier=data.get("tier", MemoryTier.WORKING),
                    metadata=data.get("metadata", {}),
                    created_at=data.get("created_at"),
                ))
            except Exception:
                pass
        return records

    def _get_short_term_memories(self, user_id: str, limit: int) -> list[MemoryRecord]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, user_id, key, value, memory_type, created_at FROM memories WHERE user_id = ? AND memory_type = ? AND created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (user_id, MemoryTier.SHORT_TERM, cutoff.isoformat(), limit),
            ).fetchall()
            return [
                MemoryRecord(r["id"], r["user_id"], r["key"], r["value"], r["memory_type"], created_at=r["created_at"])
                for r in rows
            ]

    def _get_long_term_memories(self, user_id: str, limit: int) -> list[MemoryRecord]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, user_id, key, value, memory_type, created_at FROM memories WHERE user_id = ? AND memory_type = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, MemoryTier.LONG_TERM, limit),
            ).fetchall()
            return [
                MemoryRecord(r["id"], r["user_id"], r["key"], r["value"], r["memory_type"], created_at=r["created_at"])
                for r in rows
            ]

    def _get_archive_memories(self, user_id: str, limit: int) -> list[MemoryRecord]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, user_id, key, value, memory_type, created_at FROM memories WHERE user_id = ? AND memory_type = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, MemoryTier.ARCHIVE, limit),
            ).fetchall()
            return [
                MemoryRecord(r["id"], r["user_id"], r["key"], r["value"], r["memory_type"], created_at=r["created_at"])
                for r in rows
            ]
