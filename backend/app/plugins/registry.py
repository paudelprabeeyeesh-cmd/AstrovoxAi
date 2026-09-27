"""Plugin registry for managing installed plugins."""
from __future__ import annotations

import importlib.util
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional

from .models import PluginManifest, PluginInfo, PluginStatus

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}
        self._modules: dict[str, Any] = {}

    def register(self, manifest: PluginManifest) -> PluginInfo:
        info = PluginInfo(
            id=manifest.id,
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            author=manifest.author,
            entrypoint=manifest.entrypoint,
            permissions=manifest.permissions,
            config_schema=manifest.config_schema,
            status=PluginStatus.ACTIVE,
            installed_at=datetime.now(timezone.utc),
        )
        self._plugins[manifest.id] = info
        logger.info("Registered plugin %s v%s", manifest.name, manifest.version)
        return info

    def unregister(self, plugin_id: str) -> bool:
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            self._modules.pop(plugin_id, None)
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[PluginInfo]:
        return list(self._plugins.values())

    def update_status(self, plugin_id: str, status: PluginStatus, error_message: Optional[str] = None) -> Optional[PluginInfo]:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return None
        plugin.status = status
        plugin.error_message = error_message
        return plugin

    def load_module(self, plugin_id: str, path: str) -> Any:
        if plugin_id in self._modules:
            return self._modules[plugin_id]
        try:
            spec = importlib.util.spec_from_file_location(plugin_id, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for plugin {plugin_id}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[plugin_id] = module
            spec.loader.exec_module(module)
            self._modules[plugin_id] = module
            return module
        except Exception as exc:
            logger.exception("Failed to load plugin %s", plugin_id)
            self.update_status(plugin_id, PluginStatus.ERROR, str(exc))
            raise
