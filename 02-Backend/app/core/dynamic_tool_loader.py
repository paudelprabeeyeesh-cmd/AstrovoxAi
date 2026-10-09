"""Dynamic tool loader with hot-reload support."""

from __future__ import annotations

import importlib
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DynamicToolLoader:
    """Load tools dynamically from filesystem or HTTP endpoints."""

    def __init__(self, registry, tools_dir: Optional[str] = None):
        self._registry = registry
        self._tools_dir = tools_dir or os.path.join(os.path.dirname(__file__), "..", "tools")
        self._loaded_modules: Dict[str, Any] = {}

    def load_from_filesystem(self, reload: bool = False) -> List[str]:
        loaded: List[str] = []
        if not os.path.isdir(self._tools_dir):
            return loaded
        for filename in os.listdir(self._tools_dir):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            module_name = filename[:-3]
            full_path = os.path.join(self._tools_dir, filename)
            try:
                if reload and module_name in self._loaded_modules:
                    module = importlib.reload(self._loaded_modules[module_name])
                else:
                    spec = importlib.util.spec_from_file_location(f"app.tools.{module_name}", full_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                self._loaded_modules[module_name] = module
                loaded.append(module_name)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to load tool module %s: %s", module_name, exc)
        return loaded

    def load_from_http(self, url: str) -> List[str]:
        import httpx
        loaded: List[str] = []
        try:
            response = httpx.get(url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            for tool_data in data.get("tools", []):
                name = tool_data.get("name")
                if not name:
                    continue
                handler_source = tool_data.get("handler")
                if not handler_source:
                    continue
                module_path, _, func_name = handler_source.rpartition(".")
                module = importlib.import_module(module_path)
                handler = getattr(module, func_name)
                from app.core.tool_registry_core import ToolDefinition
                tool_def = ToolDefinition(
                    name=name,
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                    version=tool_data.get("version", "1.0.0"),
                    timeout_seconds=float(tool_data.get("timeout_seconds", 30.0)),
                    tags=["http"],
                )
                self._registry.register(tool_def, handler)
                loaded.append(name)
        except Exception as exc:  # noqa: BLE001
            logger.error("HTTP tool load failed: %s", exc)
        return loaded

    def unload(self, tool_name: str) -> bool:
        return self._registry.unregister(tool_name)
