"""Plugin system for AstrovoxAi backend."""

import json
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

PLUGIN_DIR = Path(__file__).parent


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


class PluginBase(ABC):
    @abstractmethod
    async def initialize(self, context: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass


class PluginLoader:
    _plugins: Dict[str, PluginBase] = {}
    _manifests: Dict[str, PluginManifest] = {}

    @classmethod
    def load_plugin(cls, plugin_path: Path) -> Optional[PluginManifest]:
        manifest_file = plugin_path / "plugin.json"
        if not manifest_file.exists():
            return None

        try:
            with open(manifest_file, "r") as f:
                manifest_data = json.load(f)
            manifest = PluginManifest(**manifest_data)
            cls._manifests[manifest.name] = manifest

            spec = importlib.util.spec_from_file_location(
                manifest.name, plugin_path / manifest.entry_point
            )
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[manifest.name] = module
                spec.loader.exec_module(module)
                plugin_instance = getattr(module, "plugin", None)
                if plugin_instance:
                    cls._plugins[manifest.name] = plugin_instance
            return manifest
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_path}: {e}")
            return None

    @classmethod
    def load_all(cls) -> List[PluginManifest]:
        manifests = []
        for item in PLUGIN_DIR.iterdir():
            if item.is_dir() and (item / "plugin.json").exists():
                manifest = cls.load_plugin(item)
                if manifest:
                    manifests.append(manifest)
        return manifests

    @classmethod
    def get_plugin(cls, name: str) -> Optional[PluginBase]:
        return cls._plugins.get(name)

    @classmethod
    def list_plugins(cls) -> List[str]:
        return list(cls._plugins.keys())

    @classmethod
    async def initialize_all(cls, context: Dict[str, Any]) -> None:
        for plugin in cls._plugins.values():
            try:
                await plugin.initialize(context)
            except Exception as e:
                logger.error(f"Failed to initialize plugin: {e}")

    @classmethod
    async def shutdown_all(cls) -> None:
        for plugin in cls._plugins.values():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown plugin: {e}")
