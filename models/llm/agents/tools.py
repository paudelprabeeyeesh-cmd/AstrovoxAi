from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ParameterSpec:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None

    def validate(self, value: Any) -> bool:
        if self.enum is not None and value not in self.enum:
            return False
        if self.type == "string":
            return isinstance(value, str)
        if self.type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if self.type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if self.type == "boolean":
            return isinstance(value, bool)
        if self.type == "array":
            return isinstance(value, list)
        if self.type == "object":
            return isinstance(value, dict)
        return True


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
        }


class Tool(ABC):
    name: str = ""
    description: str = ""
    parameters: list[ParameterSpec] = field(default_factory=list)

    def __init__(self) -> None:
        if not self.name:
            self.name = self.__class__.__name__.lower().replace("tool", "")

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        raise NotImplementedError

    def validate_input(self, **kwargs: Any) -> ToolResult | None:
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Missing required parameter: {param.name}",
                )
            if param.name in kwargs and not param.validate(kwargs[param.name]):
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Invalid value for parameter {param.name}",
                )
        return None

    def to_schema(self) -> dict[str, Any]:
        properties = {}
        required = []
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.enum is not None:
                properties[param.name]["enum"] = param.enum
            if param.required:
                required.append(param.name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def __call__(self, **kwargs: Any) -> ToolResult:
        validation_error = self.validate_input(**kwargs)
        if validation_error is not None:
            return validation_error
        try:
            result = self.execute(**kwargs)
            if not isinstance(result, ToolResult):
                result = ToolResult(success=True, output=result)
            return result
        except Exception as exc:
            return ToolResult(success=False, output=None, error=str(exc))


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, output=None, error=f"Tool not found: {name}")
        return tool(**kwargs)
