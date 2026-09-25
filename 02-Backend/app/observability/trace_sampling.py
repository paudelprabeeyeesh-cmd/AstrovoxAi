"""Trace sampling strategy with probabilistic, rate-limiting, and adaptive sampling."""

from __future__ import annotations

import random
import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SamplingStrategy(str, Enum):
    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    PROBABILISTIC = "probabilistic"
    RATE_LIMITING = "rate_limiting"
    ADAPTIVE = "adaptive"


@dataclass
class SamplingDecision:
    trace_id: str
    sampled: bool
    strategy: SamplingStrategy
    score: float = 0.0
    reason: str = ""


class TraceSampler:
    _instance: Optional["TraceSampler"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._strategy = SamplingStrategy.PROBABILISTIC
        self._probability = 0.1
        self._rate_limit = 100
        self._rate_window = 60.0
        self._traces: List[Dict[str, Any]] = []
        self._recent_count: List[float] = []
        self._lock = threading.RLock()
        self._custom_rules: List[Callable[[Dict[str, Any]], float]] = []

    @classmethod
    def get_instance(cls) -> "TraceSampler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_strategy(self, strategy: SamplingStrategy, **kwargs: Any) -> None:
        with self._lock:
            self._strategy = strategy
            if strategy == SamplingStrategy.PROBABILISTIC:
                self._probability = kwargs.get("probability", 0.1)
            elif strategy == SamplingStrategy.RATE_LIMITING:
                self._rate_limit = kwargs.get("rate_limit", 100)
                self._rate_window = kwargs.get("rate_window", 60.0)
            elif strategy == SamplingStrategy.ADAPTIVE:
                self._probability = kwargs.get("initial_probability", 0.1)
                self._target_sample_rate = kwargs.get("target_sample_rate", 100)

    def should_sample(
        self,
        trace_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SamplingDecision:
        attributes = attributes or {}
        with self._lock:
            if self._strategy == SamplingStrategy.ALWAYS_ON:
                return SamplingDecision(
                    trace_id=trace_id,
                    sampled=True,
                    strategy=self._strategy,
                    score=1.0,
                    reason="always_on",
                )

            if self._strategy == SamplingStrategy.ALWAYS_OFF:
                return SamplingDecision(
                    trace_id=trace_id,
                    sampled=False,
                    strategy=self._strategy,
                    score=0.0,
                    reason="always_off",
                )

            if self._strategy == SamplingStrategy.PROBABILISTIC:
                score = self._apply_custom_rules(attributes)
                final_score = max(score, self._probability)
                sampled = random.random() < final_score
                return SamplingDecision(
                    trace_id=trace_id,
                    sampled=sampled,
                    strategy=self._strategy,
                    score=final_score,
                    reason="probabilistic",
                )

            if self._strategy == SamplingStrategy.RATE_LIMITING:
                now = time.time()
                cutoff = now - self._rate_window
                self._recent_count = [t for t in self._recent_count if t > cutoff]
                if len(self._recent_count) >= self._rate_limit:
                    return SamplingDecision(
                        trace_id=trace_id,
                        sampled=False,
                        strategy=self._strategy,
                        score=0.0,
                        reason="rate_limit_exceeded",
                    )
                self._recent_count.append(now)
                return SamplingDecision(
                    trace_id=trace_id,
                    sampled=True,
                    strategy=self._strategy,
                    score=1.0,
                    reason="within_rate_limit",
                )

            if self._strategy == SamplingStrategy.ADAPTIVE:
                score = self._apply_custom_rules(attributes)
                sampled = random.random() < score
                if sampled:
                    self._recent_count.append(time.time())
                self._adapt_probability()
                return SamplingDecision(
                    trace_id=trace_id,
                    sampled=sampled,
                    strategy=self._strategy,
                    score=score,
                    reason="adaptive",
                )

            return SamplingDecision(
                trace_id=trace_id,
                sampled=False,
                strategy=SamplingStrategy.ALWAYS_OFF,
                score=0.0,
                reason="unknown_strategy",
            )

    def _apply_custom_rules(self, attributes: Dict[str, Any]) -> float:
        score = 0.0
        for rule in self._custom_rules:
            try:
                score = max(score, rule(attributes))
            except Exception:
                continue
        return min(score, 1.0)

    def _adapt_probability(self) -> None:
        now = time.time()
        cutoff = now - 60.0
        recent = [t for t in self._recent_count if t > cutoff]
        current_rate = len(recent)
        if hasattr(self, "_target_sample_rate"):
            target = self._target_sample_rate
            if current_rate < target * 0.8:
                self._probability = min(self._probability * 1.1, 1.0)
            elif current_rate > target * 1.2:
                self._probability = max(self._probability * 0.9, 0.01)

    def add_custom_rule(self, rule: Callable[[Dict[str, Any]], float]) -> None:
        with self._lock:
            self._custom_rules.append(rule)

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        cutoff = now - 60.0
        recent = [t for t in self._recent_count if t > cutoff]
        return {
            "strategy": self._strategy.value,
            "probability": self._probability,
            "rate_limit": self._rate_limit,
            "samples_last_minute": len(recent),
            "custom_rules": len(self._custom_rules),
        }


sampler = TraceSampler.get_instance()
