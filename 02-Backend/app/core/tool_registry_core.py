"""Enhanced tool registry with parallel execution, caching, and timeouts."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.core.guardrails import sanitize_input
from app.core.tool_cache import ToolCache
from app.core.parallel_tool_calls import ParallelToolExecutor, ParallelToolCall

logger = logging.getLogger(__name__)


@dataclass
class ToolAnalytics:
    tool_name: str
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    last_used: Optional[str] = None
    cache_hits: int = 0


class ToolAnalyticsCollector:
    """Collects and aggregates per-tool execution analytics."""

    def __init__(self):
        self._records: Dict[str, ToolAnalytics] = {}

    def record(self, tool_name: str, success: bool, latency_ms: float, cached: bool = False, timestamp: Optional[str] = None) -> None:
        analytics = self._records.get(tool_name)
        if analytics is None:
            analytics = ToolAnalytics(tool_name=tool_name)
            self._records[tool_name] = analytics
        analytics.total_calls += 1
        if cached:
            analytics.cache_hits += 1
        if success:
            analytics.success_count += 1
        else:
            analytics.failure_count += 1
        n = analytics.total_calls
        analytics.avg_latency_ms = ((analytics.avg_latency_ms * (n - 1)) + latency_ms) / n
        analytics.last_used = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def get_stats(self, tool_name: str) -> Optional[ToolAnalytics]:
        return self._records.get(tool_name)

    def get_top_tools(self, n: int = 5, by: str = "total_calls") -> List[ToolAnalytics]:
        key = by if by in ("total_calls", "success_count", "failure_count", "avg_latency_ms", "cache_hits") else "total_calls"
        return sorted(self._records.values(), key=lambda a: getattr(a, key), reverse=True)[:n]

    def get_failure_rate(self, tool_name: str) -> float:
        analytics = self._records.get(tool_name)
        if not analytics or analytics.total_calls == 0:
            return 0.0
        return analytics.failure_count / analytics.total_calls


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    required_permissions: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    allowed_callers: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False
    tags: List[str] = field(default_factory=list)
    owner: Optional[str] = None


@dataclass
class ToolExecution:
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    sandboxed: bool = False
    cached: bool = False


class PermissionDeniedError(Exception):
    pass


class ToolRegistry:
    """Central tool registry with permission checking, sandboxing, caching, and parallel execution."""

    def __init__(self, cache: Optional[ToolCache] = None, max_parallel: int = 8):
        self.tools: Dict[str, ToolDefinition] = {}
        self.handlers: Dict[str, Callable] = {}
        self.execution_history: List[ToolExecution] = []
        self.analytics = ToolAnalyticsCollector()
        self.cache = cache or ToolCache()
        self.parallel_executor = ParallelToolExecutor(registry=self, max_concurrency=max_parallel)
        self._timeouts: Dict[str, float] = {}

    def register(self, tool_def: ToolDefinition, handler: Callable):
        self.tools[tool_def.name] = tool_def
        self.handlers[tool_def.name] = handler
        self._timeouts[tool_def.name] = tool_def.timeout_seconds
        logger.info("Registered tool: %s v%s", tool_def.name, tool_def.version)

    def unregister(self, name: str) -> bool:
        self.tools.pop(name, None)
        self.handlers.pop(name, None)
        self._timeouts.pop(name, None)
        return True

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)

    def list_tools(self, user_role: str = "user", user_id: Optional[str] = None) -> List[ToolDefinition]:
        return [t for t in self.tools.values() if not t.deprecated]

    def search_tools(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        scored = []
        for name, tool in self.tools.items():
            score = 0.0
            if query_lower in name.lower():
                score += 0.5
            if query_lower in tool.description.lower():
                score += 0.3
            for tag in tool.tags:
                if query_lower in tag.lower():
                    score += 0.2
            if score > 0:
                scored.append((score, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "name": t.name,
                "score": s,
                "description": t.description,
                "tags": t.tags,
                "version": t.version,
                "deprecated": t.deprecated,
            }
            for s, t in scored[:limit]
        ]

    def check_permissions(self, tool_name: str, user_id: str, user_roles: List[str]) -> bool:
        tool = self.tools.get(tool_name)
        if not tool:
            return False
        for perm in tool.required_permissions:
            if perm not in user_roles:
                return False
        return True

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: Optional[str] = None,
        user_roles: List[str] = None,
        request_id: Optional[str] = None,
        max_retries: int = 3,
        use_cache: bool = True,
    ) -> ToolExecution:
        user_roles = user_roles or ["user"]
        if tool_name not in self.handlers:
            return ToolExecution(tool_name=tool_name, arguments=arguments, error=f"Tool {tool_name} not found", user_id=user_id, request_id=request_id)
        tool_def = self.tools[tool_name]
        if not self.check_permissions(tool_name, user_id or "", user_roles):
            return ToolExecution(tool_name=tool_name, arguments=arguments, error=f"Permission denied for {tool_name}", user_id=user_id, request_id=request_id)
        if use_cache:
            cached = self.cache.get(tool_name, arguments)
            if cached is not None:
                latency = 0.0
                execution = ToolExecution(tool_name=tool_name, arguments=arguments, result=cached, latency_ms=latency, user_id=user_id, request_id=request_id, cached=True)
                self.execution_history.append(execution)
                self.analytics.record(tool_name=tool_name, success=True, latency_ms=latency, cached=True)
                return execution
        sanitized_args = {}
        for k, v in arguments.items():
            sanitized, _ = sanitize_input(str(v))
            sanitized_args[k] = sanitized
        start = time.perf_counter()
        for attempt in range(max_retries):
            try:
                result = self.handlers[tool_name](**sanitized_args)
                latency = (time.perf_counter() - start) * 1000
                execution = ToolExecution(tool_name=tool_name, arguments=sanitized_args, result=result, latency_ms=latency, user_id=user_id, request_id=request_id, sandboxed=tool_def.timeout_seconds > 0)
                self.execution_history.append(execution)
                self.analytics.record(tool_name=tool_name, success=True, latency_ms=latency, cached=False)
                self.cache.set(tool_name, sanitized_args, result, latency_ms=latency)
                return execution
            except PermissionDeniedError:
                latency = (time.perf_counter() - start) * 1000
                execution = ToolExecution(tool_name=tool_name, arguments=sanitized_args, error="Permission denied", latency_ms=latency, user_id=user_id, request_id=request_id)
                self.execution_history.append(execution)
                self.analytics.record(tool_name=tool_name, success=False, latency_ms=latency)
                return execution
            except Exception as _e:  # noqa: BLE001
                if attempt == max_retries - 1:
                    latency = (time.perf_counter() - start) * 1000
                    execution = ToolExecution(tool_name=tool_name, arguments=sanitized_args, error=str(_e), latency_ms=latency, user_id=user_id, request_id=request_id)
                    self.execution_history.append(execution)
                    self.analytics.record(tool_name=tool_name, success=False, latency_ms=latency)
                    return execution
                time.sleep(0.1 * (2 ** attempt))
        return ToolExecution(tool_name=tool_name, arguments=sanitized_args, error="Max retries exceeded", user_id=user_id, request_id=request_id)

    def execute_batch(self, calls: List[ParallelToolCall]) -> List[ToolExecution]:
        results = self.parallel_executor.execute_batch_sync(calls)
        return [
            ToolExecution(
                tool_name=r.tool_name,
                arguments=next((c.arguments for c in calls if c.tool_name == r.tool_name), {}),
                result=r.result,
                error=r.error,
                latency_ms=r.latency_ms,
            )
            for r in results
        ]

    def get_execution_stats(self) -> dict:
        total = len(self.execution_history)
        errors = sum(1 for e in self.execution_history if e.error is not None)
        return {
            "total_executions": total,
            "errors": errors,
            "success_rate": round((total - errors) / max(total, 1) * 100, 1),
            "tools_registered": len(self.tools),
        }


tool_registry = ToolRegistry()
