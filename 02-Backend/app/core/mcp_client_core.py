"""Enhanced MCP client with pooling and health checks."""

from __future__ import annotations

import logging
import time
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
    timeout_seconds: float = 30.0


@dataclass
class MCPResponse:
    tool_name: str
    result: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    cached: bool = False


class MCPClient:
    """Client for MCP-compatible tool servers."""

    def __init__(self, server_id: str, server_url: str, timeout: float = 30.0):
        self.server_id = server_id
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.tools: Dict[str, MCPTool] = {}
        self.client = httpx.Client(timeout=timeout)
        self._last_health: Optional[float] = None
        self._healthy: bool = True

    def discover_tools(self) -> List[MCPTool]:
        try:
            response = self.client.post(f"{self.server_url}/tools/list", json={})
            response.raise_for_status()
            data = response.json()
            tools = []
            for tool_data in data.get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", tool_data.get("input_schema", {})),
                    server_url=self.server_url,
                    timeout_seconds=float(tool_data.get("timeoutSeconds", 30.0)),
                )
                self.tools[tool.name] = tool
                tools.append(tool)
            self._healthy = True
            self._last_health = time.time()
            return tools
        except Exception as exc:  # noqa: BLE001
            self._healthy = False
            logger.error("MCP discover failed for %s: %s", self.server_id, exc)
            return []

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        if tool_name not in self.tools:
            return MCPResponse(tool_name=tool_name, error=f"Tool {tool_name} not found")
        tool = self.tools[tool_name]
        start = time.perf_counter()
        try:
            payload = {"name": tool_name, "arguments": arguments}
            response = self.client.post(f"{self.server_url}/tools/call", json=payload, timeout=tool.timeout_seconds)
            response.raise_for_status()
            result = response.json()
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(
                tool_name=tool_name,
                result=result.get("result"),
                error=result.get("error"),
                latency_ms=latency,
            )
        except httpx.HTTPStatusError as exc:
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(tool_name=tool_name, error=f"HTTP {exc.response.status_code}", latency_ms=latency)
        except Exception as exc:  # noqa: BLE001
            latency = (time.perf_counter() - start) * 1000
            return MCPResponse(tool_name=tool_name, error=str(exc), latency_ms=latency)

    def health_check(self) -> bool:
        try:
            response = self.client.get(self.server_url, timeout=5.0)
            self._healthy = response.status_code < 400
        except Exception:  # noqa: BLE001
            self._healthy = False
        self._last_health = time.time()
        return self._healthy

    def list_tools(self) -> List[MCPTool]:
        return list(self.tools.values())

    def close(self) -> None:
        self.client.close()


class MCPClientPool:
    """Pool of MCP clients with failover."""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.all_tools: Dict[str, MCPTool] = {}
        self._servers: Dict[str, str] = {}

    def add_server(self, server_id: str, server_url: str, timeout: float = 30.0) -> None:
        client = MCPClient(server_id=server_id, server_url=server_url, timeout=timeout)
        tools = client.discover_tools()
        for tool in tools:
            self.all_tools[f"{server_id}:{tool.name}"] = tool
        self.clients[server_id] = client
        self._servers[server_id] = server_url
        logger.info("Added MCP server %s with %d tools", server_id, len(tools))

    def remove_server(self, server_id: str) -> None:
        client = self.clients.pop(server_id, None)
        if client:
            client.close()
        self._servers.pop(server_id, None)
        self.all_tools = {k: v for k, v in self.all_tools.items() if not k.startswith(f"{server_id}:")}

    def call_tool(self, server_id: str, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        client = self.clients.get(server_id)
        if client is None:
            return MCPResponse(tool_name=tool_name, error=f"Server {server_id} not found")
        return client.call_tool(tool_name, arguments)

    def get_healthy_servers(self) -> List[str]:
        return [sid for sid, client in self.clients.items() if client.health_check()]


mcp_client_pool = MCPClientPool()
