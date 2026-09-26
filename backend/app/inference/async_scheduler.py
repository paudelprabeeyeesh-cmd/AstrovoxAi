"""Async inference scheduler service wrapper."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ASTROVOX_AI.ai_core.inference.async_inference_scheduler import AsyncInferenceScheduler as CoreScheduler, InferenceRequest as CoreRequest, Priority as CorePriority

logger = logging.getLogger(__name__)


class Priority(CorePriority):
    pass


class InferenceRequest(CoreRequest):
    pass


class AsyncInferenceSchedulerService:
    def __init__(self, max_batch_size: int = 32, max_queue_size: int = 1024):
        self._scheduler = CoreScheduler(max_batch_size=max_batch_size, max_queue_size=max_queue_size)

    async def submit(self, request_id: str, input_ids: Any, max_new_tokens: int, priority: Priority = Priority.NORMAL, callback: Optional[Callable] = None) -> None:
        req = CoreRequest(
            request_id=request_id,
            input_ids=input_ids,
            max_new_tokens=max_new_tokens,
            priority=priority,
            callback=callback,
        )
        await self._scheduler.submit(req)

    async def run(self, model_fn: Callable) -> None:
        await self._scheduler.run(model_fn)

    def cancel(self, request_id: str) -> bool:
        return self._scheduler.cancel(request_id)

    def stop(self) -> None:
        self._scheduler.stop()

    def get_queue_depth(self) -> Dict[str, int]:
        return self._scheduler.get_queue_depth()
