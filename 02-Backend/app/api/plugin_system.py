"""Plugin system with lifecycle hooks."""

import importlib.util
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    name: str
    event: str
    handler: Callable


@dataclass
class PluginManifest:
    name: str
    version: str
    entrypoint: str
    description: str = ""
    author: str = ""
    permissions: list[str] = field(default_factory=list)
    hooks: list[Hook] = field(default_factory=list)


@dataclass
class Plugin:
    id: str
    manifest: PluginManifest
    module: Any = None
    loaded: bool = False


class PluginManager:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._event_handlers: Dict[str, list[Hook]] = {}

    def load_plugin(self, manifest_path: str) -> Plugin:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        hooks = []
        for h in manifest_data.get("hooks", []):
            hooks.append(Hook(name=h["name"], event=h["event"], handler=lambda **kw: None))
        manifest = PluginManifest(
            name=manifest_data["name"],
            version=manifest_data["version"],
            entrypoint=manifest_data["entrypoint"],
            description=manifest_data.get("description", ""),
            author=manifest_data.get("author", ""),
            permissions=manifest_data.get("permissions", []),
            hooks=hooks,
        )
        plugin_id = str(uuid.uuid4())
        plugin = Plugin(id=plugin_id, manifest=manifest)
        if manifest.entrypoint:
            try:
                spec = importlib.util.spec_from_file_location(manifest.name, manifest.entrypoint)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                plugin.module = module
                plugin.loaded = True
            except Exception as exc:
                logger.error("Failed to load plugin %s: %s", manifest.name, exc)
                plugin.loaded = False
        self._plugins[plugin_id] = plugin
        for hook in manifest.hooks:
            self._event_handlers.setdefault(hook.event, []).append(hook)
        self._persist(plugin)
        return plugin

    def unload_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.pop(plugin_id, None)
        if not plugin:
            return False
        for hook in plugin.manifest.hooks:
            handlers = self._event_handlers.get(hook.event, [])
            self._event_handlers[hook.event] = [h for h in handlers if h.name != hook.name]
        plugin.loaded = False
        return True

    def list_plugins(self) -> list[dict]:
        return [
            {
                "id": p.id,
                "name": p.manifest.name,
                "version": p.manifest.version,
                "loaded": p.loaded,
                "permissions": p.manifest.permissions,
            }
            for p in self._plugins.values()
        ]

    def emit(self, event: str, payload: dict) -> list[Any]:
        results = []
        for hook in self._event_handlers.get(event, []):
            try:
                if hook.handler:
                    results.append(hook.handler(**payload))
            except Exception as exc:
                logger.error("Plugin hook %s failed: %s", hook.name, exc)
        return results

    def _persist(self, plugin: Plugin):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO plugins (id, name, version, entrypoint, manifest, active) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    plugin.id,
                    plugin.manifest.name,
                    plugin.manifest.version,
                    plugin.manifest.entrypoint,
                    json.dumps({
                        "description": plugin.manifest.description,
                        "permissions": plugin.manifest.permissions,
                        "hooks": [{"name": h.name, "event": h.event} for h in plugin.manifest.hooks],
                    }),
                    1 if plugin.loaded else 0,
                ),
            )
            conn.commit()


plugin_manager = PluginManager()
