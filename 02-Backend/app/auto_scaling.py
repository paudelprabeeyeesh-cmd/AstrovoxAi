"""Auto scaling logic for AstrovoxAI backend.

Provides CPU, memory, request rate, and queue depth based scaling.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScalingPolicy:
    min_instances: int = 1
    max_instances: int = 10
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0
    scale_up_cooldown: float = 60.0
    scale_down_cooldown: float = 300.0
    request_rate_threshold: int = 100
    queue_depth_threshold: int = 50


@dataclass
class MetricSample:
    cpu_percent: float
    memory_percent: float
    request_rate: float
    queue_depth: int
    timestamp: float


class AutoScaler:
    """Auto-scaling controller with multiple metrics."""

    def __init__(
        self,
        policy: Optional[ScalingPolicy] = None,
        scale_up_fn: Optional[Callable[[], int]] = None,
        scale_down_fn: Optional[Callable[[int], None]] = None,
    ):
        self.policy = policy or ScalingPolicy()
        self.scale_up_fn = scale_up_fn or (lambda: 1)
        self.scale_down_fn = scale_down_fn or (lambda _: None)
        self._current_instances = self.policy.min_instances
        self._last_scale_up = 0.0
        self._last_scale_down = 0.0
        self._samples: List[MetricSample] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def record_metrics(self, sample: MetricSample) -> None:
        with self._lock:
            self._samples.append(sample)
            if len(self._samples) > 300:
                self._samples = self._samples[-300:]

    def evaluate(self) -> Optional[str]:
        with self._lock:
            if not self._samples:
                return None
            recent = self._samples[-10:]
            avg_cpu = sum(s.cpu_percent for s in recent) / len(recent)
            avg_mem = sum(s.memory_percent for s in recent) / len(recent)
            avg_req = sum(s.request_rate for s in recent) / len(recent)
            avg_queue = sum(s.queue_depth for s in recent) / len(recent)
        now = time.time()
        scale_up_signals = 0
        if avg_cpu > self.policy.target_cpu_percent:
            scale_up_signals += 1
        if avg_mem > self.policy.target_memory_percent:
            scale_up_signals += 1
        if avg_req > self.policy.request_rate_threshold:
            scale_up_signals += 1
        if avg_queue > self.policy.queue_depth_threshold:
            scale_up_signals += 1
        if (
            scale_up_signals >= 2
            and self._current_instances < self.policy.max_instances
            and (now - self._last_scale_up) > self.policy.scale_up_cooldown
        ):
            new_instances = min(self._current_instances + 1, self.policy.max_instances)
            self._current_instances = new_instances
            self.scale_up_fn()
            self._last_scale_up = now
            logger.info("Scaled UP to %d instances", new_instances)
            return "scale_up"
        scale_down_signals = 0
        if avg_cpu < self.policy.target_cpu_percent * 0.5:
            scale_down_signals += 1
        if avg_mem < self.policy.target_memory_percent * 0.5:
            scale_down_signals += 1
        if avg_req < self.policy.request_rate_threshold * 0.3:
            scale_down_signals += 1
        if avg_queue < self.policy.queue_depth_threshold * 0.2:
            scale_down_signals += 1
        if (
            scale_down_signals >= 3
            and self._current_instances > self.policy.min_instances
            and (now - self._last_scale_down) > self.policy.scale_down_cooldown
        ):
            new_instances = max(self._current_instances - 1, self.policy.min_instances)
            self.scale_down_fn(self._current_instances - new_instances)
            self._current_instances = new_instances
            self._last_scale_down = now
            logger.info("Scaled DOWN to %d instances", new_instances)
            return "scale_down"
        return None

    def start(self, interval: float = 15.0) -> None:
        self._running = True

        def _run():
            while self._running:
                self.evaluate()
                time.sleep(interval)

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        logger.info("Auto-scaler started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def current_instances(self) -> int:
        return self._current_instances


auto_scaler = AutoScaler()
