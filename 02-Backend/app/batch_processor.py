<<<<<<< HEAD
from typing import Callable, Iterable, List, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import inspect
import time
import logging
=======
"""Batch processing for AstrovoxAI backend.

Provides efficient batching for database operations, API calls, and AI inference.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, List, Optional
>>>>>>> 10617909505295e4a37b817bb54db2364934b978

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
<<<<<<< HEAD
    batch_id: str
    total: int
    successful: int
    failed: int
    duration_ms: float
    errors: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Any] = field(default_factory=list)
    progress: List[Dict[str, Any]] = field(default_factory=list)


class BatchProcessor:
    def __init__(self, batch_size: int = 100, max_workers: int = 4, retry_count: int = 2):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.retry_count = retry_count

    def process(self, items: List[T], func: Callable[[T], R], desc: str = "Batch processing") -> BatchResult:
        return asyncio.run(self.process_async(items, func, desc))

    async def process_async(self, items: List[T], func: Callable[[T], R], desc: str = "Batch processing") -> BatchResult:
        batch_id = f"batch_{int(time.time() * 1000)}"
        total = len(items)
        successful = 0
        failed = 0
        errors: List[Dict[str, Any]] = []
        results: List[Any] = []
        progress: List[Dict[str, Any]] = []
        batches = [items[i:i + self.batch_size] for i in range(0, total, self.batch_size)]
        start = time.perf_counter()
        for batch_idx, batch in enumerate(batches):
            batch_results = await self._process_batch_async(batch, func, batch_idx)
            results.extend(batch_results.results)
            successful += batch_results.successful
            failed += batch_results.failed
            errors.extend(batch_results.errors)
            progress.append({
                "batch": batch_idx + 1,
                "total_batches": len(batches),
                "processed": len(results),
                "total": total,
            })
            logger.info("%s: batch %d/%d completed", desc, batch_idx + 1, len(batches))
        duration = (time.perf_counter() - start) * 1000
        return BatchResult(
            batch_id=batch_id,
            total=total,
            successful=successful,
            failed=failed,
            duration_ms=duration,
            errors=errors,
            results=results,
            progress=progress,
        )

    def process_stream(self, items: Iterable[T], func: Callable[[T], R], desc: str = "Stream batch processing") -> List[R]:
        return asyncio.run(self.process_stream_async(items, func, desc))

    async def process_stream_async(self, items: Iterable[T], func: Callable[[T], R], desc: str = "Stream batch processing") -> List[R]:
        results: List[R] = []
        batch: List[T] = []
        for item in items:
            batch.append(item)
            if len(batch) >= self.batch_size:
                batch_result = await self._process_batch_async(batch, func, 0)
                results.extend(batch_result.results)
                batch = []
        if batch:
            batch_result = await self._process_batch_async(batch, func, 0)
            results.extend(batch_result.results)
        return results

    def _process_batch(self, batch: List[T], func: Callable[[T], R], batch_idx: int) -> BatchResult:
        return asyncio.run(self._process_batch_async(batch, func, batch_idx))

    async def _process_batch_async(self, batch: List[T], func: Callable[[T], R], batch_idx: int) -> BatchResult:
        batch_id = f"sub_{int(time.time() * 1000)}_{batch_idx}"
        successful = 0
        failed = 0
        errors: List[Dict[str, Any]] = []
        results: List[Any] = []
        tasks = []
        for item in batch:
            tasks.append(asyncio.create_task(self._safe_execute_async(func, item)))
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
                successful += 1
            except Exception as e:
                errors.append({'item': str(item) if 'item' in dir() else 'unknown', 'error': str(e)})
                failed += 1
                logger.debug("Batch processing error: %s", e)
        return BatchResult(
            batch_id=batch_id,
            total=len(batch),
            successful=successful,
            failed=failed,
            duration_ms=0.0,
            errors=errors,
            results=results,
        )

    def _process_batch_threaded(self, batch: List[T], func: Callable[[T], R], batch_idx: int) -> BatchResult:
        batch_id = f"sub_{int(time.time() * 1000)}_{batch_idx}"
        successful = 0
        failed = 0
        errors: List[Dict[str, Any]] = []
        results: List[Any] = []
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
            future_to_item = {executor.submit(self._safe_execute, func, item): item for item in batch}
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append(result)
                    successful += 1
                except Exception as e:
                    errors.append({'item': str(item), 'error': str(e)})
                    failed += 1
                    logger.debug("Batch processing error for item %s: %s", item, e)
        return BatchResult(
            batch_id=batch_id,
            total=len(batch),
            successful=successful,
            failed=failed,
            duration_ms=0.0,
            errors=errors,
            results=results,
        )

    def _safe_execute(self, func: Callable[[T], R], item: T) -> R:
        for attempt in range(self.retry_count + 1):
            try:
                return func(item)
            except Exception:
                if attempt == self.retry_count:
                    raise
                time.sleep(0.1 * (attempt + 1))

    async def _safe_execute_async(self, func: Callable[[T], R], item: T) -> R:
        for attempt in range(self.retry_count + 1):
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(item)
                return func(item)
            except Exception:
                if attempt == self.retry_count:
                    raise
                await asyncio.sleep(0.1 * (attempt + 1))

    def parallel_map(self, func: Callable[[T], R], items: List[T]) -> List[R]:
        results: List[R] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(func, item) for item in items]
            for future in as_completed(futures):
                results.append(future.result())
        return results

    async def parallel_map_async(self, func: Callable[[T], R], items: List[T]) -> List[R]:
        tasks = [asyncio.create_task(self._safe_execute_async(func, item)) for item in items]
        return [await task for task in asyncio.as_completed(tasks)]
=======
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
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
