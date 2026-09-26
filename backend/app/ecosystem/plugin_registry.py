"""Plugin registry and lifecycle management."""
from __future__ import annotations

import importlib.util
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    entrypoint: str
    config_schema: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)


class PluginRegistry:
    def __init__(self, plugins_dir: str = "/tmp/astrovox_plugins"):
        self.plugins_dir = plugins_dir
        self._plugins: Dict[str, PluginManifest] = {}
        self._modules: Dict[str, Any] = {}
        os.makedirs(plugins_dir, exist_ok=True)

    def register(self, manifest: PluginManifest) -> None:
        self._plugins[manifest.plugin_id] = manifest

    def load(self, plugin_id: str) -> Optional[Any]:
        manifest = self._plugins.get(plugin_id)
        if not manifest:
            return None
        if plugin_id in self._modules:
            return self._modules[plugin_id]
        module_path = os.path.join(self.plugins_dir, f"{plugin_id}.py")
        if not os.path.exists(module_path):
            return None
        spec = importlib.util.spec_from_file_location(plugin_id, module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            self._modules[plugin_id] = module
            return module
        return None

    def list_plugins(self) -> List[PluginManifest]:
        return list(self._plugins.values())


plugin_registry = PluginRegistry()
