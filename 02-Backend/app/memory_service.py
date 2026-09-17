import os
import json
import uuid
import logging
from enum import Enum
from typing import Optional
from datetime import datetime

from .database import get_db

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    CONVERSATION = "conversation"
    LONG_TERM = "long_term"
    PROJECT = "project"


class MemoryService:
    def __init__(self):
        self._redis = None
        self._openai_client = None

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis as redis_lib
                self._redis = redis_lib.Redis.from_url(
                    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    decode_responses=True,
                )
                self._redis.exists("test")
            except Exception:
                self._redis = None
        return self._redis

    def _get_openai(self):
        if self._openai_client is None:
            import openai
            self._openai_client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY", "")
            )
        return self._openai_client

    def classify_memory(self, content: str, importance_score: Optional[float] = None) -> tuple:
        length = len(content)
        if importance_score is None:
            if length < 100:
                importance_score = 0.3
            elif length < 500:
                importance_score = 0.5
            elif length < 2000:
                importance_score = 0.7
            else:
                importance_score = 0.9

        if length < 50:
            memory_type = MemoryType.SHORT_TERM
        elif length < 500:
            memory_type = MemoryType.CONVERSATION
        elif length < 2000:
            memory_type = MemoryType.LONG_TERM
        else:
            memory_type = MemoryType.PROJECT

        return memory_type, importance_score

    def store_memory(
        self, user_id: str, key: str, value: str, importance_score: Optional[float] = None
    ) -> dict:
        memory_type, score = self.classify_memory(value, importance_score)

        embedding = None
        try:
            client = self._get_openai()
            response = client.embeddings.create(
                input=value, model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")

        memory_id = str(uuid.uuid4())
        with get_db() as conn:
            conn.execute(
                "INSERT INTO memories (id, user_id, key, value, embedding, memory_type, importance_score) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    memory_id,
                    user_id,
                    key,
                    value,
                    json.dumps(embedding) if embedding else None,
                    memory_type.value,
                    score,
                ),
            )
            conn.commit()

        redis_client = self._get_redis()
        if redis_client:
            try:
                cache_key = f"memory:{user_id}:{key}"
                redis_client.setex(
                    cache_key,
                    3600,
                    json.dumps(
                        {
                            "id": memory_id,
                            "key": key,
                            "value": value,
                            "memory_type": memory_type.value,
                            "importance_score": score,
                        }
                    ),
                )
            except Exception:
                pass

        return {
            "id": memory_id,
            "key": key,
            "value": value,
            "memory_type": memory_type.value,
            "importance_score": score,
        }

    def search_memories(
        self, user_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        query_lower = query.lower()
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, key, value, memory_type, importance_score, created_at FROM memories WHERE user_id = ? AND (key LIKE ? OR value LIKE ?) ORDER BY created_at DESC LIMIT ?",
                (user_id, f"%{query_lower}%", f"%{query_lower}%", limit),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "key": r["key"],
                    "value": r["value"],
                    "memory_type": r["memory_type"],
                    "importance_score": r["importance_score"],
                    "created_at": datetime.fromisoformat(r["created_at"]),
                    "similarity": 1.0,
                }
                for r in rows
            ]

    def get_relevant_memories(
        self, user_id: str, query: str, limit: int = 5
    ) -> list[dict]:
        try:
            client = self._get_openai()
            response = client.embeddings.create(
                input=query, model="text-embedding-3-small"
            )
            query_embedding = response.data[0].embedding
            embedding_str = json.dumps(query_embedding)

            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, key, value, memory_type, importance_score, created_at, 1 - (embedding <=> ?::vector) as similarity FROM memories WHERE user_id = ? AND embedding IS NOT NULL ORDER BY embedding <=> ?::vector LIMIT ?",
                    (embedding_str, user_id, embedding_str, limit),
                ).fetchall()
                return [
                    {
                        "id": r["id"],
                        "key": r["key"],
                        "value": r["value"],
                        "memory_type": r["memory_type"],
                        "importance_score": r["importance_score"],
                        "created_at": datetime.fromisoformat(r["created_at"]),
                        "similarity": float(r["similarity"]),
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"pgvector search failed: {e}")
            return self.search_memories(user_id, query, limit)


memory_service = MemoryService()

