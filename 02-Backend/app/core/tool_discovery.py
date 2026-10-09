"""Tool discovery with multiple backends."""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.tool_registry_core import ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class DiscoverySource:
    name: str
    priority: int = 0
    enabled: bool = True


class ToolDiscovery:
    """Discovers tools from multiple backends: builtins, filesystem, HTTP, MCP."""

    def __init__(self, registry):
        self._registry = registry
        self._sources: Dict[str, DiscoverySource] = {
            "builtin": DiscoverySource(name="builtin", priority=1),
            "filesystem": DiscoverySource(name="filesystem", priority=2),
            "http": DiscoverySource(name="http", priority=3),
            "mcp": DiscoverySource(name="mcp", priority=4),
        }

    def register_source(self, source: DiscoverySource) -> None:
        self._sources[source.name] = source

    def discover_all(self) -> List[ToolDefinition]:
        tools: List[ToolDefinition] = []
        for source_name, source in sorted(self._sources.items(), key=lambda x: x[1].priority):
            if not source.enabled:
                continue
            try:
                discovered = self._discover_from_source(source_name)
                tools.extend(discovered)
                logger.info("Discovered %d tools from %s", len(discovered), source_name)
            except Exception as exc:  # noqa: BLE001
                logger.error("Discovery from %s failed: %s", source_name, exc)
        return tools

    def _discover_from_source(self, source_name: str) -> List[ToolDefinition]:
        if source_name == "builtin":
            from app.tools import get_builtin_tools
            raw = get_builtin_tools()
            return [
                ToolDefinition(
                    name=t.name,
                    description=t.description,
                    parameters=t.parameters,
                    version="1.0.0",
                    tags=["builtin"],
                )
                for t in raw
            ]
        if source_name == "filesystem":
            return self._discover_filesystem()
        if source_name == "http":
            return self._discover_http()
        if source_name == "mcp":
            return self._discover_mcp()
        return []

    def _discover_filesystem(self) -> List[ToolDefinition]:
        tools: List[ToolDefinition] = []
        tools_dir = os.path.join(os.path.dirname(__file__), "..", "tools")
        if not os.path.isdir(tools_dir):
            return tools
        for filename in os.listdir(tools_dir):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"app.tools.{module_name}")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and getattr(attr, "_is_tool", False):
                        tools.append(
                            ToolDefinition(
                                name=getattr(attr, "_tool_name", attr_name),
                                description=getattr(attr, "_tool_description", ""),
                                parameters=getattr(attr, "_tool_parameters", {}),
                                version=getattr(attr, "_tool_version", "1.0.0"),
                                tags=["filesystem"],
                            )
                        )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Skip filesystem tool %s: %s", module_name, exc)
        return tools

    def _discover_http(self) -> List[ToolDefinition]:
        tools: List[ToolDefinition] = []
        registry_url = os.getenv("TOOL_REGISTRY_URL")
        if not registry_url:
            return tools
        try:
            import httpx
            response = httpx.get(f"{registry_url}/tools", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            for item in data.get("tools", []):
                tools.append(
                    ToolDefinition(
                        name=item["name"],
                        description=item.get("description", ""),
                        parameters=item.get("parameters", {}),
                        version=item.get("version", "1.0.0"),
                        timeout_seconds=float(item.get("timeout_seconds", 30.0)),
                        tags=["http"],
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("HTTP tool discovery failed: %s", exc)
        return tools

    def _discover_mcp(self) -> List[ToolDefinition]:
        tools: List[ToolDefinition] = []
        try:
            from app.core.mcp_client_core import MCPClientPool
            pool = MCPClientPool()
            for server_id, client in pool.clients.items():
                for mcp_tool in client.discover_tools():
                    tools.append(
                        ToolDefinition(
                            name=f"{server_id}:{mcp_tool.name}",
                            description=mcp_tool.description,
                            parameters=mcp_tool.input_schema,
                            version="1.0.0",
                            tags=["mcp", server_id],
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            logger.debug("MCP discovery skipped: %s", exc)
        return tools
