"""Custom tool registry and execution engine."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    success: bool
    output: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[ToolDefinition, Callable]] = {}
        self._register_builtins()

    def _register_builtins(self):
        self.register_tool(
            "web_search",
            "Search the web for information",
            parameters={"query": {"type": "string"}},
            required=["query"],
            handler=self._web_search,
        )
        self.register_tool(
            "code_executor",
            "Execute code in a sandbox",
            parameters={"language": {"type": "string"}, "code": {"type": "string"}},
            required=["language", "code"],
            handler=self._code_execute,
        )
        self.register_tool(
            "database_query",
            "Run a read-only database query",
            parameters={"sql": {"type": "string"}, "params": {"type": "array"}},
            required=["sql"],
            handler=self._db_query,
        )
        self.register_tool(
            "file_read",
            "Read a file from the workspace",
            parameters={"path": {"type": "string"}},
            required=["path"],
            handler=self._file_read,
        )
        self.register_tool(
            "file_write",
            "Write content to a file in the workspace",
            parameters={"path": {"type": "string"}, "content": {"type": "string"}},
            required=["path", "content"],
            handler=self._file_write,
        )

    def register_tool(self, name: str, description: str, parameters: dict, required: list[str], handler: Callable):
        self._tools[name] = (ToolDefinition(name=name, description=description, parameters=parameters, required=required), handler)

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        entry = self._tools.get(name)
        return entry[0] if entry else None

    def list_tools(self) -> list[ToolDefinition]:
        return [entry[0] for entry in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> ToolResult:
        entry = self._tools.get(name)
        if not entry:
            return ToolResult(success=False, error=f"Tool {name} not found")
        definition, handler = entry
        missing = [p for p in definition.required if p not in arguments]
        if missing:
            return ToolResult(success=False, error=f"Missing required parameters: {missing}")
        import time
        start = time.perf_counter()
        try:
            output = handler(**arguments)
            latency = (time.perf_counter() - start) * 1000
            return ToolResult(success=True, output=output, latency_ms=round(latency, 2))
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            logger.error("Tool %s failed: %s", name, exc)
            return ToolResult(success=False, error=str(exc), latency_ms=round(latency, 2))

    def _web_search(self, query: str) -> str:
        return f"[web search results for: {query}]"

    def _code_execute(self, language: str, code: str) -> str:
        return f"[{language} execution result]"

    def _db_query(self, sql: str, params: Optional[list] = None) -> str:
        return f"[query result for: {sql}]"

    def _file_read(self, path: str) -> str:
        return f"[file contents of {path}]"

    def _file_write(self, path: str, content: str) -> str:
        return f"[written {len(content)} bytes to {path}]"


tool_registry = ToolRegistry()
