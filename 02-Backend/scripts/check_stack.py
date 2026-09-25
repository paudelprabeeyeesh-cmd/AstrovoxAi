#!/usr/bin/env python3
"""Verify stack health."""
from __future__ import annotations

import logging
import os
import sys
import time

import redis

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_postgres() -> bool:
    try:
        with get_db() as conn:
            conn.execute("SELECT 1")
        logger.info("PostgreSQL: OK")
        return True
    except Exception as exc:
        logger.error("PostgreSQL: FAIL - %s", exc)
        return False


def check_redis() -> bool:
    try:
        client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        client.ping()
        logger.info("Redis: OK")
        return True
    except Exception as exc:
        logger.error("Redis: FAIL - %s", exc)
        return False


def wait(max_retries: int = 30, delay: float = 1.0) -> bool:
    for attempt in range(max_retries):
        if check_postgres() and check_redis():
            return True
        logger.info("Retry %s/%s", attempt + 1, max_retries)
        time.sleep(delay)
    return False


if __name__ == "__main__":
    ok = wait()
    sys.exit(0 if ok else 1)
