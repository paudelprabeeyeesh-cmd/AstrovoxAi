"""Enterprise plugin SDK — extend platform capabilities with custom plugins."""

import importlib.util
import logging
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    permissions: List[str] = field(default_factory=list)
    entrypoint: str = ""
    config_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginContext:
    tenant_id: str
    user_id: str
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Plugin:
    manifest: PluginManifest
    module: Any = None
    enabled: bool = True
    installed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class EnterprisePluginSDK:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[str]] = {}

    def register_plugin(self, manifest: PluginManifest, module: Any = None) -> Plugin:
        plugin = Plugin(manifest=manifest, module=module)
        self._plugins[manifest.plugin_id] = plugin
        logger.info("Registered plugin %s (%s)", manifest.plugin_id, manifest.name)
        return plugin

    def load_plugin_from_file(self, plugin_id: str, file_path: str) -> Optional[Plugin]:
        spec = importlib.util.spec_from_file_location(plugin_id, file_path)
        if not spec or not spec.loader:
            logger.error("Failed to load plugin from %s", file_path)
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_id] = module
        try:
            spec.loader.exec_module(module)
            manifest = getattr(module, "manifest", None)
            if not manifest:
                logger.error("Plugin %s missing manifest", plugin_id)
                return None
            return self.register_plugin(manifest, module)
        except Exception as exc:
            logger.error("Error loading plugin %s: %s", plugin_id, exc)
            return None

    def enable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.enabled = True
        logger.info("Enabled plugin %s", plugin_id)
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.enabled = False
        logger.info("Disabled plugin %s", plugin_id)
        return True

    def execute_hook(self, plugin_id: str, hook_name: str, context: PluginContext, **kwargs: Any) -> Any:
        plugin = self._plugins.get(plugin_id)
        if not plugin or not plugin.enabled:
            raise ValueError(f"Plugin {plugin_id} not found or disabled")
        if not plugin.module:
            logger.debug("No module loaded for plugin %s", plugin_id)
            return None
        handler = getattr(plugin.module, hook_name, None)
        if not handler:
            logger.warning("Hook %s not found in plugin %s", hook_name, plugin_id)
            return None
        try:
            return handler(context, **kwargs)
        except Exception as exc:
            logger.error("Hook %s failed in plugin %s: %s", hook_name, plugin_id, exc)
            raise

    def list_plugins(self, tenant_id: str = "") -> List[dict]:
        return [
            {
                "plugin_id": p.manifest.plugin_id,
                "name": p.manifest.name,
                "version": p.manifest.version,
                "description": p.manifest.description,
                "enabled": p.enabled,
                "installed_at": p.installed_at,
            }
            for p in self._plugins.values()
        ]

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)


plugin_sdk = EnterprisePluginSDK()
