"""Streaming pipeline for real-time data processing."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    event_id: str
    source: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class StreamProcessor:
    name: str
    process: Callable[..., Any]
    parallelism: int = 1
    buffer_size: int = 1000


class StreamingPipeline:
    def __init__(self) -> None:
        self._sources: Dict[str, Any] = {}
        self._processors: List[StreamProcessor] = []
        self._sinks: Dict[str, Any] = {}
        self._running: bool = False

    def add_source(self, name: str, source: Any) -> None:
        self._sources[name] = source

    def add_processor(self, processor: StreamProcessor) -> None:
        self._processors.append(processor)

    def add_sink(self, name: str, sink: Any) -> None:
        self._sinks[name] = sink

    async def run(self) -> None:
        self._running = True
        tasks = []
        for name, source in self._sources.items():
            task = asyncio.create_task(self._consume_source(name, source))
            tasks.append(task)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _consume_source(self, name: str, source: Any) -> None:
        while self._running:
            try:
                event = await self._read(source)
                if event:
                    await self._process_event(event)
            except Exception:
                logger.exception("Source %s failed", name)
            await asyncio.sleep(0.01)

    async def _process_event(self, event: StreamEvent) -> None:
        for processor in self._processors:
            try:
                result = processor.process(event.payload)
                if hasattr(result, "__await__"):
                    event.payload = await result
                else:
                    event.payload = result
            except Exception:
                logger.exception("Processor %s failed", processor.name)

    async def _read(self, source: Any) -> Optional[StreamEvent]:
        if hasattr(source, "read"):
            result = source.read()
            if hasattr(result, "__await__"):
                result = await result
            if isinstance(result, StreamEvent):
                return result
        return None

    def stop(self) -> None:
        self._running = False


streaming_pipeline = StreamingPipeline()
