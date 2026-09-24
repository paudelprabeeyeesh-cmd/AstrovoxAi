"""Parallel tool execution with asyncio and thread pool."""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sandboxing.tool_metrics import tool_metrics

logger = logging.getLogger(__name__)


@dataclass
class ParallelToolResult:
    tool_name: str
    arguments: Dict[str, Any]
    result: str
    duration_ms: float
    error: Optional[str] = None
    status: str = "success"


@dataclass
class ParallelExecutionReport:
    results: List[ParallelToolResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    tool_names: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "total_calls": len(self.results),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 4),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "tools": self.tool_names,
            "results": [
                {
                    "tool_name": r.tool_name,
                    "status": r.status,
                    "duration_ms": round(r.duration_ms, 2),
                    "error": r.error,
                }
                for r in self.results
            ],
        }


class ParallelToolExecutor:
    def __init__(self, tool_executor, max_workers: int = 8):
        self._tool_executor = tool_executor
        self._max_workers = max_workers

    def execute_parallel(
        self,
        calls: List[Dict[str, Any]],
        user_id: str,
        user_roles: Optional[List[str]] = None,
    ) -> ParallelExecutionReport:
        user_roles = user_roles or ["user"]
        start = time.perf_counter()
        results: List[ParallelToolResult] = []
        success_count = 0
        failure_count = 0
        tool_names: List[str] = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {}
            for call in calls:
                tool_name = call.get("tool_name") or call.get("name")
                arguments = call.get("arguments", call.get("input", {}))
                future = pool.submit(
                    self._safe_execute,
                    tool_name,
                    arguments,
                    user_id,
                    user_roles,
                )
                futures[future] = tool_name
                tool_names.append(tool_name)

            for future in as_completed(futures):
                tool_name = futures[future]
                try:
                    res = future.result()
                    results.append(res)
                    if res.error:
                        failure_count += 1
                    else:
                        success_count += 1
                except Exception as exc:
                    logger.error("Parallel tool execution raised for %s: %s", tool_name, exc)
                    results.append(
                        ParallelToolResult(
                            tool_name=tool_name,
                            arguments={},
                            result="",
                            duration_ms=0.0,
                            error=str(exc),
                            status="error",
                        )
                    )
                    failure_count += 1

        total_duration_ms = (time.perf_counter() - start) * 1000
        results.sort(key=lambda r: r.tool_name)
        return ParallelExecutionReport(
            results=results,
            total_duration_ms=total_duration_ms,
            success_count=success_count,
            failure_count=failure_count,
            tool_names=tool_names,
        )

    def execute_parallel_async(
        self,
        calls: List[Dict[str, Any]],
        user_id: str,
        user_roles: Optional[List[str]] = None,
    ) -> ParallelExecutionReport:
        user_roles = user_roles or ["user"]
        start = time.perf_counter()

        async def _run_all():
            loop = asyncio.get_event_loop()
            tool_names = []
            coros = []
            for call in calls:
                tool_name = call.get("tool_name") or call.get("name")
                arguments = call.get("arguments", call.get("input", {}))
                tool_names.append(tool_name)
                coros.append(
                    loop.run_in_executor(
                        None,
                        self._safe_execute,
                        tool_name,
                        arguments,
                        user_id,
                        user_roles,
                    )
                )
            return await asyncio.gather(*coros, return_exceptions=True), tool_names

        try:
            raw_results, tool_names = asyncio.run(_run_all())
        except RuntimeError:
            raw_results = []
            tool_names = []
            for call in calls:
                tool_name = call.get("tool_name") or call.get("name")
                tool_names.append(tool_name)
                raw_results.append(
                    self._safe_execute(
                        tool_name,
                        call.get("arguments", call.get("input", {})),
                        user_id,
                        user_roles,
                    )
                )

        results: List[ParallelToolResult] = []
        success_count = 0
        failure_count = 0
        for idx, raw in enumerate(raw_results):
            if isinstance(raw, Exception):
                results.append(
                    ParallelToolResult(
                        tool_name=tool_names[idx] if idx < len(tool_names) else "unknown",
                        arguments={},
                        result="",
                        duration_ms=0.0,
                        error=str(raw),
                        status="error",
                    )
                )
                failure_count += 1
            else:
                results.append(raw)
                if raw.error:
                    failure_count += 1
                else:
                    success_count += 1

        total_duration_ms = (time.perf_counter() - start) * 1000
        results.sort(key=lambda r: r.tool_name)
        return ParallelExecutionReport(
            results=results,
            total_duration_ms=total_duration_ms,
            success_count=success_count,
            failure_count=failure_count,
            tool_names=tool_names,
        )

    def _safe_execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        user_roles: List[str],
    ) -> ParallelToolResult:
        start = time.perf_counter()
        try:
            result = self._tool_executor.execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                user_roles=user_roles,
            )
            duration_ms = (time.perf_counter() - start) * 1000
            is_error = result.startswith("Error") or result.startswith("Blocked") or result.startswith("Denied")
            if is_error:
                tool_metrics.record_call(tool_name, duration_ms, "error")
            else:
                tool_metrics.record_call(tool_name, duration_ms, "success")
            return ParallelToolResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                duration_ms=duration_ms,
                error=result if is_error else None,
                status="error" if is_error else "success",
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            tool_metrics.record_call(tool_name, duration_ms, "error")
            logger.error("Parallel tool execution error for %s: %s", tool_name, exc)
            return ParallelToolResult(
                tool_name=tool_name,
                arguments=arguments,
                result="",
                duration_ms=duration_ms,
                error=str(exc),
                status="error",
            )


parallel_tool_executor = ParallelToolExecutor(tool_executor=None)
