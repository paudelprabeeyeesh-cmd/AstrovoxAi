"""Custom tool builder for creating new tools."""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import inspect


class ToolType(Enum):
    FUNCTION = "function"
    API_CALL = "api_call"
    CODE_EXECUTION = "code_execution"
    WORKFLOW = "workflow"


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class CustomTool:
    name: str
    description: str
    tool_type: ToolType
    parameters: List[ToolParameter]
    handler: Callable
    timeout: int = 30
    retry_count: int = 3
    cacheable: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class CustomToolBuilder:
    @classmethod
    def build(cls, tool: CustomTool) -> Dict[str, Any]:
        parameters_schema = {
            "type": "object",
            "properties": {},
            "required": [p.name for p in tool.parameters if p.required],
        }
        for param in tool.parameters:
            prop: Dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            parameters_schema["properties"][param.name] = prop
        return {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": parameters_schema,
            "toolType": tool.tool_type.value,
            "timeout": tool.timeout,
            "retryCount": tool.retry_count,
            "cacheable": tool.cacheable,
            "metadata": tool.metadata,
        }

    @classmethod
    def create_from_function(cls, func: Callable, name: Optional[str] = None, description: Optional[str] = None) -> CustomTool:
        tool_name = name or func.__name__
        sig = inspect.signature(func)
        parameters = []
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                param_type = param.annotation.__name__
            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,
                required=param.default == inspect.Parameter.empty,
                default=param.default if param.default != inspect.Parameter.empty else None,
            ))
        tool = CustomTool(
            name=tool_name,
            description=description or func.__doc__ or "",
            tool_type=ToolType.FUNCTION,
            parameters=parameters,
            handler=func,
        )
        return tool
