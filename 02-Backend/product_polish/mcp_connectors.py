"""
MCP Connectors - product_polish

Connect to external MCP (Model Context Protocol) servers.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MCPTool:
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class MCPResource:
    uri: str
    name: str
    mime_type: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "mime_type": self.mime_type,
            "meta": self.meta,
        }


class MCPConnector:
    """
    Base MCP connector (product_polish layer).

    Thread-safe.
    """

    def __init__(self, name: str, endpoint: str = "") -> None:
        self.name = name
        self.endpoint = endpoint
        self._lock = threading.RLock()
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}

    def register_tool(self, tool: MCPTool) -> None:
        """Register an MCP tool by name."""
        with self._lock:
            self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """Get an MCP tool by name."""
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> List[MCPTool]:
        """List all registered tools."""
        with self._lock:
            return list(self._tools.values())

    def register_resource(self, resource: MCPResource) -> None:
        """Register an MCP resource by uri."""
        with self._lock:
            self._resources[resource.uri] = resource

    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """Get a resource by uri."""
        with self._lock:
            return self._resources.get(uri)

    def list_resources(self) -> List[MCPResource]:
        """List all registered resources."""
        with self._lock:
            return list(self._resources.values())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize connector state."""
        with self._lock:
            return {
                "name": self.name,
                "endpoint": self.endpoint,
                "tools": [t.to_dict() for t in self._tools.values()],
                "resources": [r.to_dict() for r in self._resources.values()],
            }


class MCPConnectors:
    """
    Registry of named MCP connectors.

    Thread-safe.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._connectors: Dict[str, MCPConnector] = {}

    def register(self, connector: MCPConnector) -> None:
        """Register an MCP connector by name."""
        with self._lock:
            self._connectors[connector.name] = connector

    def get(self, name: str) -> Optional[MCPConnector]:
        """Get a connector by name."""
        with self._lock:
            return self._connectors.get(name)

    def list_connectors(self) -> List[MCPConnector]:
        """List all connectors."""
        with self._lock:
            return list(self._connectors.values())

    def unregister(self, name: str) -> bool:
        """Remove a connector by name."""
        with self._lock:
            return self._connectors.pop(name, None) is not None
