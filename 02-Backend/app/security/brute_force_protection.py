"""Brute-force protection for authentication endpoints.

Tracks failed login attempts per identity and locks out the account
after a configurable threshold within a time window.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LoginAttempt:
    failed_count: int = 0
    first_failed_at: float = 0.0
    locked_until: float = 0.0
    last_attempt_at: float = 0.0


@dataclass
class BruteForceConfig:
    max_attempts: int = 5
    window_seconds: float = 300.0
    lockout_seconds: float = 900.0


class BruteForceProtection:
    """In-process brute-force tracker keyed by identity (email or IP)."""

    def __init__(self, config: Optional[BruteForceConfig] = None) -> None:
        self._config = config or BruteForceConfig()
        self._records: Dict[str, LoginAttempt] = {}
        self._lock = threading.Lock()

    def _now(self) -> float:
        return time.time()

    def _cleanup(self, key: str) -> None:
        record = self._records.get(key)
        if not record:
            return
        now = self._now()
        if record.locked_until > 0 and now > record.locked_until:
            del self._records[key]
        elif record.failed_count == 0 and now - record.last_attempt_at > self._config.window_seconds:
            del self._records[key]

    def record_failure(self, key: str) -> Tuple[bool, Optional[float]]:
        now = self._now()
        with self._lock:
            self._cleanup(key)
            record = self._records.setdefault(key, LoginAttempt())
            if record.locked_until > now:
                return False, record.locked_until - now
            record.failed_count += 1
            record.last_attempt_at = now
            if record.failed_count == 1:
                record.first_failed_at = now
            if record.failed_count >= self._config.max_attempts:
                record.locked_until = now + self._config.lockout_seconds
                logger.warning("Locked out identity %r until %.0f", key, record.locked_until)
                return False, self._config.lockout_seconds
            return True, None

    def record_success(self, key: str) -> None:
        now = self._now()
        with self._lock:
            self._cleanup(key)
            if key in self._records:
                del self._records[key]

    def is_locked(self, key: str) -> Tuple[bool, Optional[float]]:
        now = self._now()
        with self._lock:
            self._cleanup(key)
            record = self._records.get(key)
            if not record:
                return False, None
            if record.locked_until > now:
                return True, record.locked_until - now
            return False, None

    def remaining_attempts(self, key: str) -> int:
        now = self._now()
        with self._lock:
            self._cleanup(key)
            record = self._records.get(key)
            if not record:
                return self._config.max_attempts
            if record.locked_until > now:
                return 0
            elapsed = now - record.first_failed_at if record.first_failed_at else 0
            if elapsed > self._config.window_seconds:
                return self._config.max_attempts
            return max(0, self._config.max_attempts - record.failed_count)


brute_force_protection = BruteForceProtection()
