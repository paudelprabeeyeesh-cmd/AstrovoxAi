import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sandboxing.tool_metrics import tool_metrics

logger = logging.getLogger(__name__)


class ToolHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


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


tool_registry = ToolRegistry()

