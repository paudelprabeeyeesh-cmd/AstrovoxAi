from __future__ import annotations

import hashlib
import logging
import math
import os
import random
import secrets
import string
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class QueryRecord:
    client_id: str
    timestamp: float
    tokens_used: int = 0
    response_hash: str = ""


@dataclass
class RateLimitConfig:
    max_requests: int = 60
    window_seconds: int = 60
    max_tokens_per_window: int = 10000
    block_duration_seconds: int = 300


class QueryRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self.config = config or RateLimitConfig()
        self.request_windows: dict[str, list[float]] = defaultdict(list)
        self.token_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self.blocked_until: dict[str, float] = {}

    def is_allowed(self, client_id: str, tokens: int = 0) -> tuple[bool, str]:
        now = time.time()
        if client_id in self.blocked_until:
            if now < self.blocked_until[client_id]:
                return False, f"Client blocked until {self.blocked_until[client_id]:.0f}"
            del self.blocked_until[client_id]
        window_start = now - self.config.window_seconds
        self.request_windows[client_id] = [t for t in self.request_windows[client_id] if t > window_start]
        if len(self.request_windows[client_id]) >= self.config.max_requests:
            self.blocked_until[client_id] = now + self.config.block_duration_seconds
            return False, "Rate limit exceeded"
        self.request_windows[client_id].append(now)
        token_window_start = now - self.config.window_seconds
        self.token_windows[client_id] = [(t, tk) for t, tk in self.token_windows[client_id] if t > token_window_start]
        current_tokens = sum(tk for _, tk in self.token_windows[client_id])
        if current_tokens + tokens > self.config.max_tokens_per_window:
            self.blocked_until[client_id] = now + self.config.block_duration_seconds
            return False, "Token limit exceeded"
        if tokens > 0:
            self.token_windows[client_id].append((now, tokens))
        return True, ""

    def reset(self, client_id: str) -> None:
        self.request_windows.pop(client_id, None)
        self.token_windows.pop(client_id, None)
        self.blocked_until.pop(client_id, None)


@dataclass
class WatermarkConfig:
    secret_key: str = field(default_factory=lambda: secrets.token_hex(16))
    green_list_size: int = 100
    epsilon: float = 0.1
    delta: float = 1e-5


class OutputWatermarker:
    def __init__(self, config: WatermarkConfig | None = None) -> None:
        self.config = config or WatermarkConfig()
        self.green_list = self._generate_green_list()
        self.logger = logging.getLogger(__name__)

    def _generate_green_list(self) -> set[str]:
        vocab = string.ascii_lowercase + string.digits + " "
        return {vocab[i % len(vocab)] for i in range(self.config.green_list_size)}

    def watermark(self, text: str) -> str:
        if not text:
            return text
        marked = list(text)
        for idx, char in enumerate(marked):
            if char.lower() in self.green_list:
                if random.random() < 0.1:
                    replacement = random.choice(list(self.green_list))
                    marked[idx] = replacement if char.islower() else replacement.upper()
        return "".join(marked)

    def detect_watermark(self, text: str) -> tuple[bool, float]:
        if not text:
            return False, 0.0
        green_hits = sum(1 for c in text.lower() if c in self.green_list)
        total = sum(1 for c in text.lower() if c.isalnum() or c == " ")
        if total == 0:
            return False, 0.0
        ratio = green_hits / total
        expected = self.config.green_list_size / (len(string.ascii_lowercase) + len(string.digits) + 1)
        z_score = (ratio - expected) / math.sqrt(expected * (1 - expected) / total) if expected > 0 else 0.0
        confidence = min(abs(z_score) / 2.0, 1.0)
        return confidence > 0.5, confidence


class APIMonitor:
    def __init__(self) -> None:
        self.records: list[QueryRecord] = []
        self.client_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"requests": 0, "tokens": 0, "errors": 0})

    def record_query(self, record: QueryRecord) -> None:
        self.records.append(record)
        stats = self.client_stats[record.client_id]
        stats["requests"] += 1
        stats["tokens"] += record.tokens_used
        if len(self.records) > 100000:
            self.records = self.records[-50000:]

    def get_client_stats(self, client_id: str) -> dict[str, Any]:
        return dict(self.client_stats.get(client_id, {"requests": 0, "tokens": 0, "errors": 0}))

    def detect_anomalies(self, client_id: str) -> list[str]:
        anomalies: list[str] = []
        stats = self.client_stats.get(client_id)
        if not stats:
            return anomalies
        if stats["requests"] > 1000:
            anomalies.append("high_volume")
        if stats["tokens"] > 1000000:
            anomalies.append("high_token_usage")
        return anomalies
