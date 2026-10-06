"""Tool calling system: dispatch and execute tool calls from agents."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ParameterSpec:
    """Specification for a tool parameter."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        return {"name": self.name, "type": self.type,
                "description": self.description, "required": self.required}


@dataclass
class Tool:
    """A registered tool callable."""
    name: str
    fn: Callable
    description: str = ""
    parameters: list[ParameterSpec] = field(default_factory=list)

    def to_spec(self) -> dict:
        return {"name": self.name, "description": self.description,
                "parameters": [p.to_dict() for p in self.parameters]}


@dataclass
class ToolResult:
    """Result returned by a tool execution."""
    success: bool = True
    output: Any = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output,
                "error": self.error, "metadata": self.metadata}


class ToolRegistry:
    """Registry of tools with validation and dispatch."""

    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, fn: Callable | None = None,
                 **decorator_kwargs) -> Callable | None:
        """Decorator to register a tool. Use as @registry.register(...) or @registry.register."""
        def wrap(f):
            name = decorator_kwargs.get("name", f.__name__)
            self.tools[name] = Tool(name=name, fn=f,
                                    description=decorator_kwargs.get("description", f.__doc__ or ""))
            return f
        if fn is not None:
            return wrap(fn)
        return wrap

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def list_tools(self) -> list[dict]:
        return [t.to_spec() for t in self.tools.values()]

    def validate_call(self, name: str, args: dict) -> tuple[bool, str | None]:
        tool = self.tools.get(name)
        if tool is None:
            return False, f"unknown tool: {name}"
        sig = inspect.signature(tool.fn)
        missing = []
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            if p.default is inspect.Parameter.empty and p.name not in args:
                missing.append(p.name)
        if missing:
            return False, f"missing parameters: {missing}"
        return True, None

    def call(self, name: str, **kwargs) -> ToolResult:
        ok, err = self.validate_call(name, kwargs)
        if not ok:
            return ToolResult(success=False, error=err)
        tool = self.tools[name]
        try:
            result = tool.fn(**kwargs)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
