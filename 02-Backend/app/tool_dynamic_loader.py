"""Dynamic tool loading from modules, plugins, and remote sources."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.tool_registry import ToolSpec, tool_registry

logger = logging.getLogger(__name__)


@dataclass
class LoadedTool:
    name: str
    source: str
    spec: ToolSpec
    loaded_at: float
    module_name: Optional[str] = None


class DynamicToolLoader:
    def __init__(self):
        self._loaded: Dict[str, LoadedTool] = {}
        self._search_paths: List[str] = []

    def add_search_path(self, path: str) -> None:
        if os.path.isdir(path) and path not in self._search_paths:
            self._search_paths.append(path)
            if path not in sys.path:
                sys.path.insert(0, path)

    def load_from_module(self, module_path: str, attribute: str = "tool_spec") -> Optional[LoadedTool]:
        try:
            spec = importlib.util.spec_from_file_location("_dynamic_tool", module_path)
            if not spec or not spec.loader:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tool_spec = getattr(module, attribute, None)
            if not isinstance(tool_spec, ToolSpec):
                logger.error("Tool spec not found or invalid in %s", module_path)
                return None
            tool_spec.handler = getattr(module, tool_spec.name.replace("-", "_") or "handler", tool_spec.handler)
            tool_registry.register_with_metadata(
                name=tool_spec.name,
                description=tool_spec.description,
                handler=tool_spec.handler,
                parameters=tool_spec.parameters,
                required_permissions=tool_spec.required_permissions,
                timeout_seconds=tool_spec.timeout_seconds,
                tags=tool_spec.tags,
                version=tool_spec.version,
                deprecated=tool_spec.deprecated,
                owner=tool_spec.owner,
            )
            loaded = LoadedTool(
                name=tool_spec.name,
                source=module_path,
                spec=tool_spec,
                loaded_at=__import__("time").time(),
                module_name=os.path.basename(module_path),
            )
            self._loaded[tool_spec.name] = loaded
            logger.info("Dynamically loaded tool %s from %s", tool_spec.name, module_path)
            return loaded
        except Exception as exc:
            logger.error("Failed to load tool from %s: %s", module_path, exc)
            return None

    def load_from_plugin(self, plugin_name: str, tool_specs: List[ToolSpec]) -> List[LoadedTool]:
        loaded_tools: List[LoadedTool] = []
        for spec in tool_specs:
            try:
                tool_registry.register_with_metadata(
                    name=spec.name,
                    description=spec.description,
                    handler=spec.handler,
                    parameters=spec.parameters,
                    required_permissions=spec.required_permissions,
                    timeout_seconds=spec.timeout_seconds,
                    tags=spec.tags,
                    version=spec.version,
                    deprecated=spec.deprecated,
                    owner=plugin_name,
                )
                loaded = LoadedTool(
                    name=spec.name,
                    source=f"plugin:{plugin_name}",
                    spec=spec,
                    loaded_at=__import__("time").time(),
                    module_name=plugin_name,
                )
                self._loaded[spec.name] = loaded
                loaded_tools.append(loaded)
                logger.info("Loaded tool %s from plugin %s", spec.name, plugin_name)
            except Exception as exc:
                logger.error("Failed to load tool %s from plugin %s: %s", spec.name, plugin_name, exc)
        return loaded_tools

    def load_from_callable(self, name: str, func: Callable, description: str, **kwargs) -> LoadedTool:
        import inspect
        sig = inspect.signature(func)
        parameters = {
            "type": "object",
            "properties": {
                p.name: {"type": "string"}
                for p in sig.parameters.values()
                if p.default == inspect.Parameter.empty
            },
            "required": [
                p.name for p in sig.parameters.values()
                if p.default == inspect.Parameter.empty
            ],
        }
        spec = ToolSpec(
            name=name,
            description=description,
            parameters=parameters,
            handler=func,
            required_permissions=kwargs.get("required_permissions", []),
            timeout_seconds=kwargs.get("timeout_seconds", 30.0),
            tags=kwargs.get("tags", []),
            version=kwargs.get("version", "1.0.0"),
            deprecated=kwargs.get("deprecated", False),
            owner=kwargs.get("owner"),
        )
        tool_registry.register_with_metadata(
            name=spec.name,
            description=spec.description,
            handler=spec.handler,
            parameters=spec.parameters,
            required_permissions=spec.required_permissions,
            timeout_seconds=spec.timeout_seconds,
            tags=spec.tags,
            version=spec.version,
            deprecated=spec.deprecated,
            owner=spec.owner,
        )
        loaded = LoadedTool(
            name=name,
            source="callable",
            spec=spec,
            loaded_at=__import__("time").time(),
        )
        self._loaded[name] = loaded
        logger.info("Dynamically loaded tool %s from callable", name)
        return loaded

    def discover_and_load(self) -> List[LoadedTool]:
        loaded_tools: List[LoadedTool] = []
        for path in self._search_paths:
            if not os.path.isdir(path):
                continue
            for filename in os.listdir(path):
                if not filename.endswith(".py") or filename.startswith("_"):
                    continue
                module_path = os.path.join(path, filename)
                tool = self.load_from_module(module_path)
                if tool:
                    loaded_tools.append(tool)
        return loaded_tools

    def get_loaded_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": lt.name,
                "source": lt.source,
                "version": lt.spec.version,
                "description": lt.spec.description,
                "tags": lt.spec.tags,
                "owner": lt.spec.owner,
                "loaded_at": lt.loaded_at,
            }
            for lt in self._loaded.values()
        ]

    def unload(self, tool_name: str) -> bool:
        loaded = self._loaded.pop(tool_name, None)
        if not loaded:
            return False
        tool_registry.deregister(tool_name)
        logger.info("Unloaded dynamic tool %s", tool_name)
        return True


dynamic_tool_loader = DynamicToolLoader()
