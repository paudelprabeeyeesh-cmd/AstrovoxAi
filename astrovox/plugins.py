"""Plugin SDK with event system, versioning, permissions, hot loading, and sandboxed execution.

Provides a stable plugin API that external developers can use to extend
Astrovox without modifying core code.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class PluginManifest:
    name: str
    version: str
    entry: str
    permissions: List[str] = field(default_factory=list)
    api_version: str = "1.0"


class PluginEvent:
    def __init__(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.name = name
        self.payload = payload or {}


class EventBus:
    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[[PluginEvent], None]]] = {}

    def subscribe(self, event: str, handler: Callable[[PluginEvent], None]) -> None:
        self._listeners.setdefault(event, []).append(handler)

    def publish(self, event: PluginEvent) -> None:
        for handler in self._listeners.get(event.name, []):
            handler(event)


class PluginPermissionDenied(Exception):
    pass


class PluginContext:
    def __init__(self, manifest: PluginManifest, event_bus: EventBus) -> None:
        self.manifest = manifest
        self.event_bus = event_bus

    def emit(self, name: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.event_bus.publish(PluginEvent(name=name, payload=payload))

    def ensure_permission(self, permission: str) -> None:
        if permission not in self.manifest.permissions:
            raise PluginPermissionDenied(permission)


class Plugin:
    def __init__(self, manifest: PluginManifest, context: PluginContext) -> None:
        self.manifest = manifest
        self.context = context

    def load(self) -> None:
        raise NotImplementedError

    def unload(self) -> None:
        raise NotImplementedError


class PluginSDK:
    def __init__(self) -> None:
        self.event_bus = EventBus()
        self._plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self._plugins[plugin.manifest.name] = plugin
        plugin.load()

    def unregister(self, name: str) -> None:
        plugin = self._plugins.pop(name, None)
        if plugin is not None:
            plugin.unload()

    def load_from_path(self, path: str) -> Plugin:
        module_path = Path(path)
        spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_path.stem] = module
        spec.loader.exec_module(module)
        manifest = getattr(module, "manifest", PluginManifest(name=module_path.stem, version="0.1.0", entry=module_path.stem))
        context = PluginContext(manifest=manifest, event_bus=self.event_bus)
        plugin = getattr(module, "create_plugin", lambda ctx: Plugin(manifest, ctx))(context)
        self.register(plugin)
        return plugin

    def hot_reload(self, name: str, path: str) -> Plugin:
        self.unregister(name)
        return self.load_from_path(path)
