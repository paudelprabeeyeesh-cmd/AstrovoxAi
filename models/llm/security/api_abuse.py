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
class RateLimitConfig:
    max_requests: int = 60
    window_seconds: int = 60
    max_tokens_per_window: int = 10000
    block_duration_seconds: int = 300


@dataclass
class APIKeyRecord:
    key_id: str
    owner: str
    created_at: float
    last_used: float = 0.0
    request_count: int = 0
    is_blocked: bool = False
    blocked_until: float = 0.0


class APIRateLimiter:
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
            logger.warning("API rate limit exceeded for %s: %d/%d", client_id, len(self.request_windows[client_id]), self.config.max_requests)
            return False, "Rate limit exceeded"
        self.request_windows[client_id].append(now)
        token_window_start = now - self.config.window_seconds
        self.token_windows[client_id] = [(t, tk) for t, tk in self.token_windows[client_id] if t > token_window_start]
        current_tokens = sum(tk for _, tk in self.token_windows[client_id])
        if current_tokens + tokens > self.config.max_tokens_per_window:
            self.blocked_until[client_id] = now + self.config.block_duration_seconds
            logger.warning("API token limit exceeded for %s", client_id)
            return False, "Token limit exceeded"
        if tokens > 0:
            self.token_windows[client_id].append((now, tokens))
        return True, ""

    def reset(self, client_id: str) -> None:
        self.request_windows.pop(client_id, None)
        self.token_windows.pop(client_id, None)
        self.blocked_until.pop(client_id, None)


@dataclass
class AnomalyDetectionResult:
    is_anomalous: bool
    anomaly_score: float
    anomaly_type: str
    details: dict[str, Any] = field(default_factory=dict)


class APIAnomalyDetector:
    def __init__(self) -> None:
        self.request_log: list[dict[str, Any]] = []
        self.client_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"requests": 0, "tokens": 0, "errors": 0, "avg_interval": 0.0, "last_request": 0.0})

    def record_request(self, client_id: str, tokens: int = 0, status: str = "success") -> None:
        now = time.time()
        self.request_log.append({"client_id": client_id, "timestamp": now, "tokens": tokens, "status": status})
        stats = self.client_stats[client_id]
        stats["requests"] += 1
        stats["tokens"] += tokens
        if status != "success":
            stats["errors"] += 1
        if stats["last_request"] > 0:
            interval = now - stats["last_request"]
            stats["avg_interval"] = (stats["avg_interval"] * (stats["requests"] - 1) + interval) / stats["requests"]
        stats["last_request"] = now
        if len(self.request_log) > 100000:
            self.request_log = self.request_log[-50000:]

    def detect(self, client_id: str) -> AnomalyDetectionResult:
        stats = self.client_stats.get(client_id)
        if not stats or stats["requests"] < 5:
            return AnomalyDetectionResult(is_anomalous=False, anomaly_score=0.0, anomaly_type="insufficient_data")
        anomalies: list[str] = []
        score = 0.0
        if stats["requests"] > 500:
            anomalies.append("volume_spike")
            score += 0.4
        if stats["tokens"] > 500000:
            anomalies.append("token_spike")
            score += 0.3
        error_rate = stats["errors"] / stats["requests"] if stats["requests"] > 0 else 0.0
        if error_rate > 0.5:
            anomalies.append("high_error_rate")
            score += 0.3
        if stats["avg_interval"] > 0 and stats["requests"] / (time.time() - stats.get("last_request", time.time()) + stats["avg_interval"]) > 10:
            anomalies.append("burst_pattern")
            score += 0.2
        score = min(score, 1.0)
        return AnomalyDetectionResult(is_anomalous=score > 0.5, anomaly_score=score, anomaly_type=", ".join(anomalies) if anomalies else "normal", details=dict(stats))


class AutomatedBlocker:
    def __init__(self, cooldown_seconds: int = 600, violation_threshold: int = 5) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.violation_threshold = violation_threshold
        self.blocked_clients: dict[str, float] = {}
        self.block_counts: dict[str, int] = defaultdict(int)

    def should_block(self, client_id: str) -> tuple[bool, str]:
        if client_id in self.blocked_clients:
            if time.time() < self.blocked_clients[client_id]:
                return True, f"Client {client_id} is blocked"
            del self.blocked_clients[client_id]
        if self.block_counts[client_id] >= self.violation_threshold:
            self.blocked_clients[client_id] = time.time() + self.cooldown_seconds
            logger.warning("Automatically blocking client %s after %d violations", client_id, self.block_counts[client_id])
            return True, f"Client {client_id} blocked after repeated violations"
        return False, ""

    def record_violation(self, client_id: str) -> None:
        self.block_counts[client_id] += 1

    def unblock(self, client_id: str) -> None:
        self.blocked_clients.pop(client_id, None)
        self.block_counts.pop(client_id, None)
