"""MCP client SDK."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import aiohttp


@dataclass
class MCPClientConfig:
    server_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    retry_count: int = 3


@dataclass
class MCPRequest:
    id: str
    method: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class MCPClient:
    def __init__(self, config: MCPClientConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> None:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        self._session = aiohttp.ClientSession(headers=headers)

    async def disconnect(self) -> None:
        if self._session:
            await self._session.close()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResponse:
        request = MCPRequest(
            id=str(__import__("uuid").uuid4()),
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        return await self._send_request(request)

    async def list_tools(self) -> List[Dict[str, Any]]:
        request = MCPRequest(id=str(__import__("uuid").uuid4()), method="tools/list")
        response = await self._send_request(request)
        return response.result.get("tools", []) if response.result else []

    async def read_resource(self, uri: str) -> MCPResponse:
        request = MCPRequest(
            id=str(__import__("uuid").uuid4()),
            method="resources/read",
            params={"uri": uri},
        )
        return await self._send_request(request)

    async def _send_request(self, request: MCPRequest) -> MCPResponse:
        if not self._session:
            await self.connect()
        try:
            async with self._session.post(
                self.config.server_url,
                json={"jsonrpc": "2.0", "id": request.id, "method": request.method, "params": request.params},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            ) as resp:
                data = await resp.json()
                return MCPResponse(
                    id=data.get("id", request.id),
                    result=data.get("result"),
                    error=data.get("error"),
                )
        except Exception as e:
            return MCPResponse(id=request.id, error={"message": str(e)})
