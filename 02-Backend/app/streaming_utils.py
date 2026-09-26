"""Token streaming utilities for inference responses."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Callable, Optional

from .sse_streaming import simple_stream

logger = logging.getLogger(__name__)


@dataclass
class StreamChunk:
    token: str
    index: int
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class StreamBufferConfig:
    max_buffer_size: int = 64
    flush_interval_ms: int = 50
    max_chunk_size: int = 4


class TokenStreamBuffer:
    def __init__(self, config: Optional[StreamBufferConfig] = None):
        self.config = config or StreamBufferConfig()
        self._buffer: deque[str] = deque(maxlen=self.config.max_buffer_size)
        self._lock = asyncio.Lock()
        self._closed = False

    async def add_token(self, token: str) -> Optional[str]:
        async with self._lock:
            if self._closed:
                return None
            self._buffer.append(token)
            if len(self._buffer) >= self.config.max_chunk_size:
                chunk = "".join(self._buffer)
                self._buffer.clear()
                return chunk
            return None

    async def flush(self) -> str:
        async with self._lock:
            chunk = "".join(self._buffer)
            self._buffer.clear()
            return chunk

    async def close(self) -> None:
        self._closed = True
        async with self._lock:
            remaining = "".join(self._buffer)
            self._buffer.clear()
            if remaining:
                logger.debug("Flushing remaining %d tokens on stream close", len(remaining))


class StreamingHelper:
    def __init__(self, buffer_config: Optional[StreamBufferConfig] = None):
        self.buffer = TokenStreamBuffer(buffer_config)
        self._start_time: Optional[float] = None
        self._tokens_sent = 0
        self._bytes_sent = 0

    async def stream_tokens(
        self,
        token_source: AsyncGenerator[str, None],
        chunk_emitter: Callable[[str], None],
        metadata_emitter: Optional[Callable[[dict], None]] = None,
    ) -> dict[str, Any]:
        self._start_time = time.time()
        buffer_task = asyncio.create_task(self._buffer_flusher(chunk_emitter))
        try:
            async for token in token_source:
                chunk = await self.buffer.add_token(token)
                if chunk:
                    self._tokens_sent += len(chunk)
                    self._bytes_sent += len(chunk.encode("utf-8"))
                    chunk_emitter(chunk)
                    if metadata_emitter:
                        metadata_emitter({"type": "chunk", "tokens": self._tokens_sent})
            final = await self.buffer.flush()
            if final:
                self._tokens_sent += len(final)
                self._bytes_sent += len(final.encode("utf-8"))
                chunk_emitter(final)
            elapsed_ms = (time.time() - self._start_time) * 1000
            stats = {
                "tokens_sent": self._tokens_sent,
                "bytes_sent": self._bytes_sent,
                "elapsed_ms": round(elapsed_ms, 2),
                "tokens_per_second": round(self._tokens_sent / (elapsed_ms / 1000), 2) if elapsed_ms > 0 else 0,
            }
            if metadata_emitter:
                metadata_emitter({"type": "complete", "stats": stats})
            return stats
        finally:
            buffer_task.cancel()
            try:
                await buffer_task
            except asyncio.CancelledError:
                pass
            await self.buffer.close()

    async def _buffer_flusher(self, chunk_emitter: Callable[[str], None]) -> None:
        try:
            while True:
                await asyncio.sleep(self.buffer.config.flush_interval_ms / 1000)
                chunk = await self.buffer.flush()
                if chunk:
                    chunk_emitter(chunk)
        except asyncio.CancelledError:
            pass

    async def create_sse_stream(
        self,
        token_source: AsyncGenerator[str, None],
    ) -> AsyncGenerator[str, None]:
        async def _pipeline():
            async for item in simple_stream(token_source):
                yield item
            yield "data: [DONE]\n\n"

        async for event in _pipeline():
            yield event


class BackpressureController:
    def __init__(self, max_pending: int = 32, high_water_mark: int = 16):
        self.max_pending = max_pending
        self.high_water_mark = high_water_mark
        self._pending = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            if self._pending >= self.max_pending:
                return False
            self._pending += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            self._pending = max(0, self._pending - 1)

    @property
    def pending_count(self) -> int:
        return self._pending

    @property
    def should_throttle(self) -> bool:
        return self._pending >= self.high_water_mark
