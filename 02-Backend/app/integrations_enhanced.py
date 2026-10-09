"""Enhanced integrations with external API support."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.external_apis import external_api_client
from app.mcp_client import MCPClientPool

logger = logging.getLogger(__name__)


def register_external_api(name: str, base_url: str, api_key: Optional[str] = None, **kwargs) -> None:
    from app.external_apis import ExternalAPIEndpoint
    endpoint = ExternalAPIEndpoint(name=name, base_url=base_url, api_key=api_key, **kwargs)
    external_api_client.register_endpoint(endpoint)


def call_external_api(endpoint_name: str, path: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    response = external_api_client.call(endpoint_name, path, method=method, **kwargs)
    return {
        "endpoint": response.endpoint_name,
        "status_code": response.status_code,
        "body": response.body,
        "latency_ms": response.latency_ms,
        "success": response.success,
        "error": response.error,
    }


def get_mcp_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "server_id": t.server_url,
            "parameters": t.input_schema,
        }
        for t in MCPClientPool().all_tools.values()
    ]


def call_mcp_tool(server_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    response = MCPClientPool().call_tool(server_id, tool_name, arguments)
    return {
        "tool_name": response.tool_name,
        "result": response.result,
        "error": response.error,
        "latency_ms": response.latency_ms,
        "cached": response.cached,
    }
