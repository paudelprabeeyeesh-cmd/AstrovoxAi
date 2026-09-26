"""MCP (Model Context Protocol) server."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    annotations: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResource:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"


@dataclass
class MCPPrompt:
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)


class MCPServer:
    _tools: Dict[str, MCPTool] = {}
    _resources: Dict[str, MCPResource] = {}
    _prompts: Dict[str, MCPPrompt] = {}

    @classmethod
    def register_tool(cls, tool: MCPTool) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def register_resource(cls, resource: MCPResource) -> None:
        cls._resources[resource.uri] = resource

    @classmethod
    def register_prompt(cls, prompt: MCPPrompt) -> None:
        cls._prompts[prompt.name] = prompt

    @classmethod
    def list_tools(cls) -> List[MCPTool]:
        return list(cls._tools.values())

    @classmethod
    def list_resources(cls) -> List[MCPResource]:
        return list(cls._resources.values())

    @classmethod
    def list_prompts(cls) -> List[MCPPrompt]:
        return list(cls._prompts.values())

    @classmethod
    def get_tool(cls, name: str) -> Optional[MCPTool]:
        return cls._tools.get(name)

    @classmethod
    def get_resource(cls, uri: str) -> Optional[MCPResource]:
        return cls._resources.get(uri)

    @classmethod
    def get_prompt(cls, name: str) -> Optional[MCPPrompt]:
        return cls._prompts.get(name)
