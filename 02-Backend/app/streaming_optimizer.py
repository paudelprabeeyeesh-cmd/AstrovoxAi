"""Streaming optimization for AstrovoxAI backend.

Provides token batching, compression, and adaptive streaming strategies.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamMetrics:
    tokens_sent: int = 0
    bytes_sent: int = 0
    first_token_ms: float = 0.0
    total_duration_ms: float = 0.0
    compression_ratio: float = 1.0
    reconnect_count: int = 0


class StreamingOptimizer:
    """Optimizes streaming responses with batching and compression."""

    def __init__(self, batch_size: int = 4, batch_delay_ms: int = 10, enable_compression: bool = True):
        self.batch_size = batch_size
        self.batch_delay = batch_delay_ms / 1000.0
        self.enable_compression = enable_compression
        self._metrics: Dict[str, StreamMetrics] = {}

    def optimize_token_stream(self, stream_id: str, token_source: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        metrics = StreamMetrics()
        self._metrics[stream_id] = metrics
        buffer: List[str] = []
        start = time.perf_counter()
        try:
            first_yielded = False
            async for token in token_source:
                if not first_yielded:
                    metrics.first_token_ms = (time.perf_counter() - start) * 1000
                    first_yielded = True
                buffer.append(token)
                metrics.tokens_sent += 1
                if len(buffer) >= self.batch_size:
                    batch = "".join(buffer)
                    if self.enable_compression:
                        batch = self._compress(batch)
                    metrics.bytes_sent += len(batch.encode("utf-8"))
                    yield batch
                    buffer = []
                    await asyncio.sleep(self.batch_delay)
            if buffer:
                batch = "".join(buffer)
                if self.enable_compression:
                    batch = self._compress(batch)
                metrics.bytes_sent += len(batch.encode("utf-8"))
                yield batch
        except asyncio.CancelledError:
            metrics.reconnect_count += 1
            raise
        finally:
            metrics.total_duration_ms = (time.perf_counter() - start) * 1000

    def _compress(self, text: str) -> str:
        if not self.enable_compression:
            return text
        return text.replace("\n\n", "\n").strip()

    def get_metrics(self, stream_id: str) -> Optional[StreamMetrics]:
        return self._metrics.get(stream_id)

    def reset_metrics(self, stream_id: str) -> None:
        self._metrics.pop(stream_id, None)

    def get_average_ttft(self) -> float:
        if not self._metrics:
            return 0.0
        return sum(m.first_token_ms for m in self._metrics.values()) / len(self._metrics)

    def get_average_throughput(self) -> float:
        if not self._metrics:
            return 0.0
        total_tokens = sum(m.tokens_sent for m in self._metrics.values())
        total_time = sum(m.total_duration_ms for m in self._metrics.values() if m.total_duration_ms > 0)
        return total_tokens / (total_time / 1000.0) if total_time else 0.0


streaming_optimizer = StreamingOptimizer()
