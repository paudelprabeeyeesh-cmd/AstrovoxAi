"""
MCP (Model Context Protocol) client for external tool servers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_url: str


@dataclass
class MCPResponse:
    tool_name: str
    result: Any
    error: Optional[str] = None
    latency_ms: float = 0.0


class MCPClient:
    """Client for MCP-compatible tool servers."""

    def __init__(self, server_url: str, timeout: float = 30.0):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.tools: Dict[str, MCPTool] = {}
        self.client = httpx.Client(timeout=timeout)

    def discover_tools(self) -> List[MCPTool]:
        """Discover available tools from MCP server."""
        try:
            response = self.client.post(f"{self.server_url}/tools/list", json={})
            response.raise_for_status()
            data = response.json()
            tools = []
            for tool_data in data.get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("input_schema", {}),
                    server_url=self.server_url,
                )
                self.tools[tool.name] = tool
                tools.append(tool)
            return tools
        except Exception as e:
            logger.error(f"Failed to discover tools from {self.server_url}: {e}")
            return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        """Call a tool on the MCP server."""
        if tool_name not in self.tools:
            return MCPResponse(tool_name=tool_name, result=None, error=f"Tool {tool_name} not found")
        import time
        start = time.perf_counter()
        try:
            payload = {"name": tool_name, "arguments": arguments}
            response = self.client.post(f"{self.server_url}/tools/call", json=payload)
            response.raise_for_status()
            result = response.json()
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(tool_name=tool_name, result=result.get("result"), error=result.get("error"), latency_ms=latency)
        except httpx.HTTPStatusError as e:
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(tool_name=tool_name, result=None, error=f"HTTP {e.response.status_code}", latency_ms=latency)
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(tool_name=tool_name, result=None, error=str(e), latency_ms=latency)

    def list_tools(self) -> List[MCPTool]:
        return list(self.tools.values())

    def close(self):
        self.client.close()


class MCPClientPool:
    """Pool of MCP clients for multiple servers."""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.all_tools: Dict[str, MCPTool] = {}

    def add_server(self, server_id: str, server_url: str):
        client = MCPClient(server_url=server_url)
        tools = client.discover_tools()
        for tool in tools:
            self.all_tools[f"{server_id}:{tool.name}"] = tool
        self.clients[server_id] = client
        logger.info("Added MCP server %s with %d tools", server_id, len(tools))

    def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        client = self.clients.get(server_id)
        if client is None:
            return MCPResponse(tool_name=tool_name, result=None, error=f"Server {server_id} not found")
        return client.call_tool(tool_name, arguments)
