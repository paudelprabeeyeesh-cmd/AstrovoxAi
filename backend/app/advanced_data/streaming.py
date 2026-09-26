"""Streaming data pipeline."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class StreamProcessor:
    def __init__(self, name: str):
        self.name = name
        self._handlers: List[Callable[[Any], None]] = []

    def add_handler(self, handler: Callable[[Any], None]) -> None:
        self._handlers.append(handler)

    async def process(self, record: Any) -> None:
        for handler in self._handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(record)
                else:
                    handler(record)
            except Exception:
                logger.exception("stream handler failed in %s", self.name)


class StreamingPipeline:
    def __init__(self) -> None:
        self._processors: Dict[str, StreamProcessor] = {}

    def add_processor(self, name: str, processor: StreamProcessor) -> None:
        self._processors[name] = processor

    async def publish(self, processor_name: str, record: Any) -> None:
        processor = self._processors.get(processor_name)
        if processor:
            await processor.process(record)


streaming_pipeline = StreamingPipeline()
