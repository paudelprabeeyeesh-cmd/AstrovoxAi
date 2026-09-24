"""Parallel tool execution with concurrency limits."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ParallelToolCall:
    tool_name: str
    arguments: Dict[str, Any]
    user_id: Optional[str] = None
    user_roles: Optional[List[str]] = None


@dataclass
class ParallelToolResult:
    tool_name: str
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class ParallelToolExecutor:
    """Execute multiple tools concurrently with bounded concurrency."""

    def __init__(self, registry, max_concurrency: int = 8):
        self._registry = registry
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._max_concurrency = max_concurrency

    async def execute_batch(
        self,
        calls: List[ParallelToolCall],
        max_retries: int = 2,
    ) -> List[ParallelToolResult]:
        if not calls:
            return []
        tasks = [self._execute_one(call, max_retries) for call in calls]
        return list(await asyncio.gather(*tasks, return_exceptions=False))

    async def _execute_one(self, call: ParallelToolCall, max_retries: int) -> ParallelToolResult:
        async with self._semaphore:
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._registry.execute(
                        tool_name=call.tool_name,
                        arguments=call.arguments,
                        user_id=call.user_id,
                        user_roles=call.user_roles or ["user"],
                        max_retries=max_retries,
                    ),
                )
                return ParallelToolResult(
                    tool_name=call.tool_name,
                    result=result.result,
                    error=result.error,
                    latency_ms=result.latency_ms,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Parallel tool execution failed for %s: %s", call.tool_name, exc)
                return ParallelToolResult(tool_name=call.tool_name, error=str(exc))

    def execute_batch_sync(
        self,
        calls: List[ParallelToolCall],
        max_retries: int = 2,
    ) -> List[ParallelToolResult]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("Already in async context")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.execute_batch(calls, max_retries=max_retries))
        finally:
            loop.close()
