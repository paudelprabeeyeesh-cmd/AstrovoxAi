import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamingIngestionConfig:
    buffer_size: int = 1024
    flush_interval_ms: int = 1000
    max_concurrency: int = 8
    checkpoint_path: str = "./streaming_checkpoints"
    enable_backpressure: bool = True


@dataclass
class StreamRecord:
    source: str
    payload: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


class StreamingIngestionPipeline:
    def __init__(self, config: Optional[StreamingIngestionConfig] = None):
        self.config = config or StreamingIngestionConfig()
        self.buffer: List[StreamRecord] = []
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._semaphore = asyncio.Semaphore(self.config.max_concurrency)
        logger.info(
            "Streaming ingestion pipeline initialized: buffer_size=%d, max_concurrency=%d",
            self.config.buffer_size,
            self.config.max_concurrency,
        )

    def register_handler(self, source: str, handler: Callable) -> None:
        self._handlers.setdefault(source, []).append(handler)

    async def _process_record(self, record: StreamRecord) -> None:
        handlers = self._handlers.get(record.source, [])
        async with self._semaphore:
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(record)
                    else:
                        handler(record)
                except Exception as exc:
                    logger.warning("Handler failed for %s: %s", record.source, exc)

    async def ingest(self, records: List[StreamRecord]) -> Dict[str, Any]:
        processed = 0
        failed = 0
        tasks = []
        for record in records:
            if len(self.buffer) >= self.config.buffer_size:
                self.buffer.pop(0)
            self.buffer.append(record)
            tasks.append(self._process_record(record))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                failed += 1
            else:
                processed += 1
        return {"processed": processed, "failed": failed, "buffer_len": len(self.buffer)}

    async def ingest_stream(self, record_generator) -> Dict[str, Any]:
        total_processed = 0
        total_failed = 0
        async for batch in record_generator:
            result = await self.ingest(batch)
            total_processed += result["processed"]
            total_failed += result["failed"]
        return {"processed": total_processed, "failed": total_failed}

    def checkpoint(self) -> str:
        import os
        os.makedirs(self.config.checkpoint_path, exist_ok=True)
        path = os.path.join(self.config.checkpoint_path, "stream_state.json")
        data = {
            "buffer": [
                {"source": r.source, "payload": r.payload, "metadata": r.metadata}
                for r in self.buffer
            ]
        }
        with open(path, "w") as f:
            json.dump(data, f)
        logger.info("Stream checkpoint saved to %s", path)
        return path
