import httpx
import json
from typing import List, Dict, Any, Optional


class MCPClient:
    def __init__(self, server_url: str = ""):
        self.server_url = server_url.rstrip("/")
        self._client = httpx.Client(timeout=30)

    def connect(self, server_url: str) -> bool:
        try:
            self.server_url = server_url.rstrip("/")
            response = self._client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except Exception:
            return False

    def list_tools(self) -> List[Dict[str, Any]]:
        if not self.server_url:
            raise RuntimeError("Not connected")
        response = self._client.get(f"{self.server_url}/tools")
        response.raise_for_status()
        return response.json().get("tools", [])

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        if not self.server_url:
            raise RuntimeError("Not connected")
        response = self._client.post(
            f"{self.server_url}/tools/{tool_name}/call",
            json={"arguments": arguments},
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict):
            return json.dumps(result.get("result", result))
        return json.dumps(result)

    def disconnect(self):
        try:
            self._client.close()
        except Exception:
            pass
        self.server_url = ""
