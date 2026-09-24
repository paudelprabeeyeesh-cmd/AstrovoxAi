"""Enhanced distributed queue with priority, retries, and dead-letter support.

Built on Redis Streams with consumer groups for reliable processing.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class JobPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


PRIORITY_ORDER = {
    JobPriority.CRITICAL: 0,
    JobPriority.HIGH: 1,
    JobPriority.NORMAL: 2,
    JobPriority.LOW: 3,
}


@dataclass
class QueueJob:
    job_id: str
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL
    status: str = "queued"
    created_at: float = field(default_factory=time.time)
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    result: Optional[Any] = None


class DistributedQueue:
    """Redis Streams based distributed queue with consumer groups."""

    def __init__(self, redis_url: Optional[str] = None, stream_prefix: str = "astrovox:queue"):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.stream_prefix = stream_prefix
        self._group = "astrovox-workers"
        self._client = self._init_client()

    def _init_client(self) -> Any:
        try:
            import redis
            return redis.Redis.from_url(self.redis_url, decode_responses=True)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis client init failed: %s", exc)
            return None

    def _stream_key(self, priority: JobPriority) -> str:
        return f"{self.stream_prefix}:{priority.value}"

    def enqueue(self, payload: Dict[str, Any], priority: JobPriority = JobPriority.NORMAL) -> str:
        job_id = str(uuid.uuid4())
        job_data = {
            "job_id": job_id,
            "payload": json.dumps(payload, default=str),
            "priority": priority.value,
            "status": "queued",
            "created_at": str(time.time()),
            "attempts": "0",
        }
        stream_key = self._stream_key(priority)
        try:
            self._client.xadd(stream_key, job_data, maxlen=10000, approximate=True)
            job_key = f"{self.stream_prefix}:job:{job_id}"
            self._client.hset(job_key, mapping={k: str(v) for k, v in job_data.items()})
            self._client.expire(job_key, 86400)
            logger.debug("Enqueued job %s with priority %s", job_id, priority.value)
            return job_id
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to enqueue job: %s", exc)
            raise

    def dequeue(self, consumer_name: str = "worker-1", timeout_ms: int = 5000) -> Optional[QueueJob]:
        priorities = sorted(PRIORITY_ORDER.keys(), key=lambda p: PRIORITY_ORDER[p])
        for priority in priorities:
            stream_key = self._stream_key(priority)
            try:
                self._client.xgroup_create(stream_key, self._group, id="$", mkstream=True)
            except Exception:  # noqa: BLE001
                pass
            messages = self._client.xreadgroup(
                groupname=self._group,
                consumername=consumer_name,
                streams={stream_key: ">"},
                count=1,
                block=timeout_ms // max(len(priorities), 1),
            )
            if messages:
                for stream, entries in messages:
                    for message_id, data in entries:
                        self._client.xack(stream_key, self._group, message_id)
                        job = QueueJob(
                            job_id=data.get("job_id", str(uuid.uuid4())),
                            payload=json.loads(data.get("payload", "{}")),
                            priority=JobPriority(data.get("priority", JobPriority.NORMAL.value)),
                            status="processing",
                            created_at=float(data.get("created_at", time.time())),
                            attempts=int(data.get("attempts", 0)) + 1,
                        )
                        job_key = f"{self.stream_prefix}:job:{job.job_id}"
                        self._client.hset(
                            job_key,
                            mapping={
                                "status": job.status,
                                "attempts": str(job.attempts),
                            },
                        )
                        return job
        return None

    def ack(self, job_id: str) -> None:
        pass

    def nack(self, job_id: str, error: str) -> None:
        job_key = f"{self.stream_prefix}:job:{job_id}"
        try:
            self._client.hset(job_key, "status", "failed")
            self._client.hset(job_key, "error", error)
            dlq_key = f"{self.stream_prefix}:dlq"
            self._client.rpush(dlq_key, json.dumps({"job_id": job_id, "error": error}))
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to nack job %s: %s", job_id, exc)

    def get_status(self, job_id: str) -> Dict[str, Any]:
        job_key = f"{self.stream_prefix}:job:{job_id}"
        try:
            data = self._client.hgetall(job_key)
            if data:
                data["payload"] = json.loads(data.get("payload", "{}"))
                return data
            return {"job_id": job_id, "status": "not_found"}
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to get job status: %s", exc)
            return {"job_id": job_id, "status": "error", "error": str(exc)}

    def requeue(self, job_id: str) -> bool:
        job_key = f"{self.stream_prefix}:job:{job_id}"
        try:
            data = self._client.hgetall(job_key)
            if not data:
                return False
            payload = json.loads(data.get("payload", "{}"))
            priority = JobPriority(data.get("priority", JobPriority.NORMAL.value))
            self.enqueue(payload, priority=priority)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to requeue job %s: %s", job_id, exc)
            return False


distributed_queue = DistributedQueue()
