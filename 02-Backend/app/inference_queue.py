
import json
import logging
import time
import uuid
from typing import Any

import redis

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}


class InferenceQueue:
    def __init__(self, redis_url: str = None):
        url = redis_url or "redis://localhost:6379"
        self._redis = redis.Redis.from_url(url, decode_responses=True)
        self._stream_prefix = "inference:stream"
        self._group = "inference_workers"
        self._job_prefix = "inference:job"
        self._maxlen = 10000

    def _stream_key(self, priority: str) -> str:
        return f"{self._stream_prefix}:{priority}"

    def enqueue_job(self, user_id: str, prompt: str, model: str, priority: str = "normal") -> str:
        job_id = str(uuid.uuid4())
        timestamp = time.time()
        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "prompt": prompt,
            "model": model,
            "priority": priority,
            "status": "queued",
            "created_at": timestamp,
            "attempts": "0",
        }
        stream_key = self._stream_key(priority)
        try:
            self._redis.xadd(stream_key, job_data, maxlen=self._maxlen, approximate=True)
            self._redis.hset(f"{self._job_prefix}:{job_id}", mapping=job_data)
            self._redis.expire(f"{self._job_prefix}:{job_id}", 3600)
            logger.debug("Enqueued job %s with priority %s", job_id, priority)
            return job_id
        except Exception as exc:
            logger.error("Failed to enqueue job: %s", exc)
            raise

    def dequeue_job(self, consumer_name: str = "worker-1", timeout_ms: int = 5000) -> dict | None:
        priorities = sorted(PRIORITY_ORDER.keys(), key=lambda p: PRIORITY_ORDER[p])
        for priority in priorities:
            stream_key = self._stream_key(priority)
            try:
                self._redis.xgroup_create(stream_key, self._group, id="$", mkstream=True)
            except redis.exceptions.ResponseError:
                pass
            messages = self._redis.xreadgroup(
                groupname=self._group,
                consumername=consumer_name,
                streams={stream_key: ">"},
                count=1,
                block=timeout_ms // len(priorities) if priorities else timeout_ms,
            )
            if messages:
                for stream, entries in messages:
                    for message_id, data in entries:
                        self._redis.xack(stream_key, self._group, message_id)
                        job = dict(data)
                        job["_stream"] = stream
                        job["_message_id"] = message_id
                        job["status"] = "processing"
                        job["attempts"] = str(int(job.get("attempts", 0)) + 1)
                        self._redis.hset(f"{self._job_prefix}:{job['job_id']}", mapping=job)
                        return job
        return None

    def get_job_status(self, job_id: str) -> dict:
        key = f"{self._job_prefix}:{job_id}"
        data = self._redis.hgetall(key)
        if not data:
            return {"job_id": job_id, "status": "not_found"}
        return {k: v for k, v in data.items()}

    def mark_completed(self, job_id: str, result: Any = None):
        key = f"{self._job_prefix}:{job_id}"
        self._redis.hset(key, "status", "completed")
        if result is not None:
            self._redis.hset(key, "result", json.dumps(result, default=str))

    def mark_failed(self, job_id: str, error: str):
        key = f"{self._job_prefix}:{job_id}"
        self._redis.hset(key, "status", "failed")
        self._redis.hset(key, "error", error)
