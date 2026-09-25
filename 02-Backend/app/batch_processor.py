from typing import TypeVar, Callable, Iterable, List, Optional, Dict, Any
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import inspect
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
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
