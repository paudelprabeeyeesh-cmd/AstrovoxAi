"""Batch processing for AstrovoxAI backend.

Provides efficient batching for database operations, API calls, and AI inference.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    total: int
    succeeded: int
    failed: int
    duration_ms: float
    errors: List[Dict[str, Any]]


class BatchProcessor:
    """Process items in batches with concurrency control."""

    def __init__(
        self,
        batch_size: int = 32,
        concurrency: int = 4,
        retry_count: int = 2,
        retry_delay: float = 0.5,
    ):
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.retry_count = retry_count
        self.retry_delay = retry_delay

    async def process(self, items: List[Any], handler: Callable[[Any], Coroutine]) -> BatchResult:
        start = time.perf_counter()
        semaphore = asyncio.Semaphore(self.concurrency)
        errors: List[Dict[str, Any]] = []
        succeeded = 0
        failed = 0

        async def _process(item: Any) -> None:
            nonlocal succeeded, failed
            async with semaphore:
                for attempt in range(self.retry_count + 1):
                    try:
                        await handler(item)
                        succeeded += 1
                        return
                    except Exception as exc:  # noqa: BLE001
                        if attempt < self.retry_count:
                            await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        else:
                            failed += 1
                            errors.append({"item": str(item)[:128], "error": str(exc)})

        batches = [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]
        for batch in batches:
            await asyncio.gather(*[_process(item) for item in batch])
        duration = (time.perf_counter() - start) * 1000
        logger.info("Batch processed %d items in %.2fms (succeeded=%d, failed=%d)", len(items), duration, succeeded, failed)
        return BatchResult(
            total=len(items),
            succeeded=succeeded,
            failed=failed,
            duration_ms=duration,
            errors=errors,
        )

    def process_sync(self, items: List[Any], handler: Callable[[Any], Any]) -> BatchResult:
        start = time.perf_counter()
        errors = []
        succeeded = 0
        failed = 0
        for item in items:
            for attempt in range(self.retry_count + 1):
                try:
                    handler(item)
                    succeeded += 1
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < self.retry_count:
                        time.sleep(self.retry_delay * (2 ** attempt))
                    else:
                        failed += 1
                        errors.append({"item": str(item)[:128], "error": str(exc)})
        duration = (time.perf_counter() - start) * 1000
        return BatchResult(total=len(items), succeeded=succeeded, failed=failed, duration_ms=duration, errors=errors)


batch_processor = BatchProcessor()
