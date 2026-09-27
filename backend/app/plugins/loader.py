"""Plugin loader with hot reloading support."""
from __future__ import annotations

import importlib.util
import logging
import os
import sys
from typing import Any, Optional

from .registry import PluginRegistry
from .models import PluginManifest, PluginStatus

logger = logging.getLogger(__name__)


class PluginLoader:
    def __init__(self, plugins_dir: str = "./plugins") -> None:
        self._plugins_dir = plugins_dir
        self._registry = PluginRegistry()
        os.makedirs(plugins_dir, exist_ok=True)

    def discover(self) -> list[str]:
        discovered = []
        for root, _, files in os.walk(self._plugins_dir):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    discovered.append(os.path.join(root, file))
        return discovered

    def load_plugin(self, path: str) -> PluginManifest:
        module_name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        manifest = getattr(module, "PLUGIN_MANIFEST", None)
        if not manifest:
            raise ValueError(f"Plugin {path} does not define PLUGIN_MANIFEST")
        self._registry.register(manifest)
        self._registry.load_module(manifest.id, path)
        logger.info("Loaded plugin %s from %s", manifest.name, path)
        return manifest

    def load_all(self) -> list[PluginManifest]:
        manifests = []
        for path in self.discover():
            try:
                manifest = self.load_plugin(path)
                manifests.append(manifest)
            except Exception as exc:
                logger.error("Failed to load plugin %s: %s", path, exc)
        return manifests

    def reload_plugin(self, plugin_id: str) -> bool:
        plugin = self._registry.get_plugin(plugin_id)
        if not plugin:
            return False
        path = os.path.join(self._plugins_dir, f"{plugin_id}.py")
        if not os.path.exists(path):
            return False
        self._registry.update_status(plugin_id, PluginStatus.ACTIVE)
        self._registry.load_module(plugin_id, path)
        logger.info("Reloaded plugin %s", plugin_id)
        return True

    def execute(self, plugin_id: str, method: str, params: dict) -> dict:
        plugin = self._registry.get_plugin(plugin_id)
        if not plugin or plugin.status != PluginStatus.ACTIVE:
            raise ValueError(f"Plugin {plugin_id} is not active")
        module = self._registry.load_module(plugin_id, plugin.entrypoint)
        func = getattr(module, method, None)
        if not func or not callable(func):
            raise AttributeError(f"Plugin {plugin_id} does not expose method {method}")
        return func(**params)
