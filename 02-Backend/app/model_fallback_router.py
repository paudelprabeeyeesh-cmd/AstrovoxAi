"""Model fallback router with health-aware routing."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelHealth:
    model_id: str
    is_healthy: bool = True
    latency_ms: float = 0.0
    last_error: Optional[str] = None
    last_checked: float = field(default_factory=time.time)
    failure_count: int = 0
    success_count: int = 0


@dataclass
class FallbackRule:
    primary: str
    fallbacks: list[str]
    max_retries: int = 2
    retry_delay: float = 1.0


class ModelFallbackRouter:
    def __init__(self):
        self._models: dict[str, ModelHealth] = {}
        self._rules: dict[str, FallbackRule] = {}
        self._default_rule = FallbackRule(primary="gpt-4o-mini", fallbacks=["gpt-4o", "claude-3-haiku"])

    def register_model(self, model_id: str) -> None:
        if model_id not in self._models:
            self._models[model_id] = ModelHealth(model_id=model_id)

    def add_rule(self, rule_id: str, rule: FallbackRule) -> None:
        self._rules[rule_id] = rule
        self.register_model(rule.primary)
        for m in rule.fallbacks:
            self.register_model(m)

    def record_success(self, model_id: str, latency_ms: float = 0.0) -> None:
        health = self._models.get(model_id)
        if health:
            health.is_healthy = True
            health.latency_ms = latency_ms
            health.last_checked = time.time()
            health.success_count += 1
            health.failure_count = 0

    def record_failure(self, model_id: str, error: Optional[str] = None) -> None:
        health = self._models.get(model_id)
        if health:
            health.is_healthy = False
            health.last_error = error
            health.last_checked = time.time()
            health.failure_count += 1
            logger.warning("Model %s marked unhealthy: %s", model_id, error)

    def get_route(self, rule_id: Optional[str] = None) -> list[str]:
        rule = self._rules.get(rule_id) if rule_id else self._default_rule
        if not rule:
            return [self._default_rule.primary] + self._default_rule.fallbacks
        candidates = [rule.primary] + rule.fallbacks
        healthy = [m for m in candidates if self._models.get(m, ModelHealth(model_id=m)).is_healthy]
        return healthy if healthy else candidates

    def route(self, rule_id: Optional[str] = None) -> str:
        candidates = self.get_route(rule_id)
        return candidates[0] if candidates else self._default_rule.primary

    def get_health_report(self) -> dict[str, Any]:
        return {
            model_id: {
                "is_healthy": h.is_healthy,
                "latency_ms": h.latency_ms,
                "failure_count": h.failure_count,
                "success_count": h.success_count,
                "last_error": h.last_error,
            }
            for model_id, h in self._models.items()
        }
