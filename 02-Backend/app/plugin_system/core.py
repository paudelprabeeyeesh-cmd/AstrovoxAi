"""Plugin system with lifecycle management."""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginStatus(str, Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    FAILED = "failed"


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    entrypoint: str = ""
    tags: List[str] = field(default_factory=list)


class Plugin:
    """Runtime plugin instance."""

    def __init__(self, manifest: PluginManifest, module: Optional[Any] = None):
        self.manifest = manifest
        self.module = module
        self.status = PluginStatus.INSTALLED

    def enable(self) -> None:
        self.status = PluginStatus.ENABLED
        if self.module and hasattr(self.module, "on_enable"):
            self.module.on_enable()

    def disable(self) -> None:
        self.status = PluginStatus.DISABLED
        if self.module and hasattr(self.module, "on_disable"):
            self.module.on_disable()


class PluginSystem:
    """Plugin registry with install, enable, disable, uninstall."""

    def __init__(self, plugins_dir: Optional[str] = None):
        self._plugins_dir = plugins_dir or os.path.join(os.path.dirname(__file__), "..", "plugin_system", "plugins")
        self._plugins: Dict[str, Plugin] = {}

    def install(self, manifest: PluginManifest) -> Plugin:
        if manifest.name in self._plugins:
            raise ValueError(f"Plugin {manifest.name} already installed")
        plugin = Plugin(manifest=manifest)
        self._plugins[manifest.name] = plugin
        logger.info("Installed plugin %s v%s", manifest.name, manifest.version)
        return plugin

    def load(self, plugin_name: str) -> Optional[Plugin]:
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return None
        if plugin.module is None and plugin.manifest.entrypoint:
            self._load_module(plugin)
        return plugin

    def _load_module(self, plugin: Plugin) -> None:
        entrypoint = plugin.manifest.entrypoint
        if not entrypoint or not os.path.isfile(entrypoint):
            return
        try:
            spec = importlib.util.spec_from_file_location(plugin.manifest.name, entrypoint)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin.module = module
            plugin.status = PluginStatus.ENABLED
            logger.info("Loaded plugin module for %s", plugin.manifest.name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load plugin module %s: %s", plugin.manifest.name, exc)
            plugin.status = PluginStatus.FAILED

    def enable(self, plugin_name: str) -> bool:
        plugin = self.load(plugin_name)
        if not plugin:
            return False
        plugin.enable()
        return True

    def disable(self, plugin_name: str) -> bool:
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return False
        plugin.disable()
        return True

    def uninstall(self, plugin_name: str) -> bool:
        plugin = self._plugins.pop(plugin_name, None)
        if not plugin:
            return False
        plugin.disable()
        logger.info("Uninstalled plugin %s", plugin_name)
        return True

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": p.manifest.name,
                "version": p.manifest.version,
                "status": p.status.value,
                "tags": p.manifest.tags,
            }
            for p in self._plugins.values()
        ]


plugin_system = PluginSystem()
