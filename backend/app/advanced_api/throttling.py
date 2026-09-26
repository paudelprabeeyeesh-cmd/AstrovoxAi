"""Request throttling for API protection."""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ThrottleConfig:
    key: str
    max_requests: int
    per_seconds: float
    action: str = "drop"


class RequestThrottler:
    def __init__(self) -> None:
        self._configs: Dict[str, ThrottleConfig] = {}
        self._requests: Dict[str, List[float]] = {}

    def add_config(self, config: ThrottleConfig) -> None:
        self._configs[config.key] = config

    def check(self, key: str) -> str:
        config = self._configs.get(key)
        if not config:
            return "allow"
        now = time.time()
        history = self._requests.setdefault(key, [])
        history[:] = [t for t in history if now - t < config.per_seconds]
        if len(history) >= config.max_requests:
            return config.action
        history.append(now)
        return "allow"


request_throttler = RequestThrottler()
