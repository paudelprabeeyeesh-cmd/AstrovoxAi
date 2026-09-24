import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from app.tool_cache import tool_cache
from sandboxing.tool_metrics import tool_metrics

logger = logging.getLogger(__name__)


class ToolHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ToolExecutionResult:
    tool_name: str
    result: str
    duration_ms: float
    status: str = "success"
    error: Optional[str] = None
    cached: bool = False


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable[..., Any]] = field(default=None, repr=False, compare=False)
    required_permissions: List[str] = field(default_factory=list)
    timeout_seconds: float = 30.0
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False
    owner: Optional[str] = None
    registered_at: float = field(default_factory=time.time)
    last_health_check: Optional[float] = None
    health_status: ToolHealthStatus = ToolHealthStatus.UNKNOWN

    def to_openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}
        self._tags: Dict[str, List[str]] = {}

    def register(self, tool: Any) -> None:
        name = getattr(tool, "name", None)
        if not name:
            raise ValueError("Tool must have a name attribute")
        spec = ToolSpec(
            name=name,
            description=getattr(tool, "description", ""),
            parameters=getattr(tool, "parameters", {}),
            handler=getattr(tool, "function", None),
            required_permissions=getattr(tool, "required_permissions", []),
            timeout_seconds=getattr(tool, "timeout_seconds", 30.0),
            tags=getattr(tool, "tags", []),
            version=getattr(tool, "version", "1.0.0"),
            deprecated=getattr(tool, "deprecated", False),
        )
        self._tools[name] = spec
        for tag in spec.tags:
            self._tags.setdefault(tag, []).append(name)
        logger.info("Registered tool: %s", name)

    def register_with_metadata(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        parameters: Optional[Dict[str, Any]] = None,
        required_permissions: Optional[List[str]] = None,
        timeout_seconds: float = 30.0,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
        deprecated: bool = False,
        owner: Optional[str] = None,
    ) -> None:
        spec = ToolSpec(
            name=name,
            description=description,
            parameters=parameters or {},
            handler=handler,
            required_permissions=required_permissions or [],
            timeout_seconds=timeout_seconds,
            tags=tags or [],
            version=version,
            deprecated=deprecated,
            owner=owner,
        )
        self._tools[name] = spec
        for tag in spec.tags:
            self._tags.setdefault(tag, []).append(name)
        logger.info("Registered tool with metadata: %s", name)

    def get(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def search(self, query: str, limit: int = 10) -> List[dict]:
        query_lower = query.lower()
        scored = []
        for name, tool in self._tools.items():
            score = 0.0
            if query_lower in name.lower():
                score += 0.5
            desc = tool.description.lower()
            if query_lower in desc:
                score += 0.3
            for tag in tool.tags:
                if query_lower in tag.lower():
                    score += 0.2
            if score > 0:
                scored.append((score, name, tool))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "name": name,
                "score": score,
                "description": tool.description,
                "tags": tool.tags,
                "version": tool.version,
                "deprecated": tool.deprecated,
                "schema": tool.to_openai_schema() if tool.handler else None,
            }
            for score, name, tool in scored[:limit]
        ]

    def list_all(self) -> List[dict]:
        return [
            {
                "name": name,
                "description": tool.description,
                "tags": tool.tags,
                "version": tool.version,
                "deprecated": tool.deprecated,
                "required_permissions": tool.required_permissions,
                "owner": tool.owner,
                "timeout_seconds": tool.timeout_seconds,
            }
            for name, tool in self._tools.items()
        ]

    def list_by_tag(self, tag: str) -> List[ToolSpec]:
        names = self._tags.get(tag, [])
        return [self._tools[name] for name in names if name in self._tools]

    def check_permission(self, tool_name: str, user_roles: List[str]) -> bool:
        tool = self._tools.get(tool_name)
        if not tool:
            return False
        for perm in tool.required_permissions:
            if perm not in user_roles:
                return False
        return True

    def update_health(self, tool_name: str, status: ToolHealthStatus) -> None:
        tool = self._tools.get(tool_name)
        if tool:
            tool.health_status = status
            tool.last_health_check = time.time()

    def get_unhealthy_tools(self) -> List[ToolSpec]:
        return [t for t in self._tools.values() if t.health_status == ToolHealthStatus.UNHEALTHY]

    def deregister(self, tool_name: str) -> bool:
        tool = self._tools.pop(tool_name, None)
        if not tool:
            return False
        for tag in tool.tags:
            names = self._tags.get(tag, [])
            if tool_name in names:
                names.remove(tool_name)
        logger.info("Deregistered tool: %s", tool_name)
        return True

    def get_metrics_summary(self) -> Dict[str, Any]:
        all_metrics = tool_metrics.get_all()
        summary = {
            "total_tools": len(self._tools),
            "registered_tools": len(self._tools),
            "deprecated_tools": sum(1 for t in self._tools.values() if t.deprecated),
            "tags": list(self._tags.keys()),
            "metrics_available": len(all_metrics),
        }
        return summary

    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> ToolExecutionResult:
        start = time.perf_counter()
        tool = self._tools.get(tool_name)
        if not tool:
            duration_ms = (time.perf_counter() - start) * 1000
            tool_metrics.record_call(tool_name, duration_ms, "error")
            return ToolExecutionResult(
                tool_name=tool_name,
                result=f"Error: tool '{tool_name}' not found",
                duration_ms=duration_ms,
                status="error",
                error="tool_not_found",
            )
        if use_cache and tool.timeout_seconds > 0:
            cached_result = tool_cache.get(tool_name, arguments)
            if cached_result is not None:
                duration_ms = (time.perf_counter() - start) * 1000
                tool_metrics.record_call(tool_name, duration_ms, "cached")
                return ToolExecutionResult(
                    tool_name=tool_name,
                    result=cached_result,
                    duration_ms=duration_ms,
                    status="success",
                    cached=True,
                )
        if not tool.handler:
            duration_ms = (time.perf_counter() - start) * 1000
            return ToolExecutionResult(
                tool_name=tool_name,
                result="Error: tool has no handler",
                duration_ms=duration_ms,
                status="error",
                error="no_handler",
            )
        try:
            if tool_name in ("search_documents", "create_memory"):
                result = tool.handler(user_id=user_id, **arguments)
            else:
                result = tool.handler(**arguments)
            duration_ms = (time.perf_counter() - start) * 1000
            tool_metrics.record_call(tool_name, duration_ms, "success")
            if use_cache and tool.timeout_seconds > 0:
                tool_cache.set(tool_name, arguments, str(result), ttl=cache_ttl)
            return ToolExecutionResult(
                tool_name=tool_name,
                result=str(result),
                duration_ms=duration_ms,
                status="success",
            )
        except Exception as _e:
            duration_ms = (time.perf_counter() - start) * 1000
            tool_metrics.record_call(tool_name, duration_ms, "error")
            logger.error("Tool execution error for %s: %s", tool_name, _e)
            return ToolExecutionResult(
                tool_name=tool_name,
                result=f"Error executing {tool_name}: {_e}",
                duration_ms=duration_ms,
                status="error",
                error=str(_e),
            )

    def execute_parallel(
        self,
        calls: List[Dict[str, Any]],
        user_id: str,
        max_workers: int = 8,
    ) -> List[ToolExecutionResult]:
        results: List[ToolExecutionResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {}
            for call in calls:
                tool_name = call.get("tool_name") or call.get("name")
                arguments = call.get("arguments", call.get("input", {}))
                future = pool.submit(
                    self.execute,
                    tool_name=tool_name,
                    arguments=arguments,
                    user_id=user_id,
                    use_cache=True,
                )
                futures[future] = tool_name
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    results.append(
                        ToolExecutionResult(
                            tool_name=futures[future],
                            result=f"Error: {exc}",
                            duration_ms=0.0,
                            status="error",
                            error=str(exc),
                        )
                    )
        return results

    def load_from_source(self, module_path: str, attribute: str = "tool_spec") -> Optional[ToolSpec]:
        try:
            from app.tool_dynamic_loader import dynamic_tool_loader
            loaded = dynamic_tool_loader.load_from_module(module_path, attribute=attribute)
            return loaded.spec if loaded else None
        except Exception as exc:
            logger.error("Failed to dynamically load tool from %s: %s", module_path, exc)
            return None


tool_registry = ToolRegistry()

