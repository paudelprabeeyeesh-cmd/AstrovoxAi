"""Model warmup and health probe for inference endpoints."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelHealthStatus:
    model_id: str
    is_healthy: bool
    latency_ms: float
    last_probe: float = field(default_factory=time.time)
    error: Optional[str] = None
    warmup_completed: bool = False


class ModelHealthProbe:
    def __init__(self):
        self._statuses: dict[str, ModelHealthStatus] = {}
        self._warmup_lock = asyncio.Lock()

    async def probe(self, model_id: str, health_check_fn) -> ModelHealthStatus:
        start = time.time()
        try:
            await asyncio.wait_for(health_check_fn(), timeout=10.0)
            latency = (time.time() - start) * 1000
            status = ModelHealthStatus(model_id=model_id, is_healthy=True, latency_ms=latency)
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = ModelHealthStatus(model_id=model_id, is_healthy=False, latency_ms=latency, error=str(e))
            logger.warning("Health probe failed for %s: %s", model_id, e)
        self._statuses[model_id] = status
        return status

    async def warmup(self, model_id: str, warmup_fn) -> ModelHealthStatus:
        async with self._warmup_lock:
            start = time.time()
            try:
                await asyncio.wait_for(warmup_fn(), timeout=30.0)
                latency = (time.time() - start) * 1000
                status = ModelHealthStatus(model_id=model_id, is_healthy=True, latency_ms=latency, warmup_completed=True)
                logger.info("Model %s warmed up in %.2fms", model_id, latency)
            except Exception as e:
                latency = (time.time() - start) * 1000
                status = ModelHealthStatus(model_id=model_id, is_healthy=False, latency_ms=latency, error=str(e))
                logger.error("Model %s warmup failed: %s", model_id, e)
            self._statuses[model_id] = status
            return status

    def get_status(self, model_id: str) -> Optional[ModelHealthStatus]:
        return self._statuses.get(model_id)

    def get_all_statuses(self) -> dict[str, dict[str, Any]]:
        return {
            model_id: {
                "is_healthy": s.is_healthy,
                "latency_ms": round(s.latency_ms, 2),
                "last_probe": s.last_probe,
                "error": s.error,
                "warmup_completed": s.warmup_completed,
            }
            for model_id, s in self._statuses.items()
        }

    def is_healthy(self, model_id: str) -> bool:
        status = self._statuses.get(model_id)
        return status.is_healthy if status else False
