"""
Plugin architecture with registration, lifecycle, and hook system.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Type


class PluginStatus(Enum):
    LOADED = auto()
    ACTIVE = auto()
    DISABLED = auto()
    FAILED = auto()


HookHandler = Callable[..., Any]


@dataclass
class Plugin:
    name: str
    version: str = "0.1.0"
    status: PluginStatus = PluginStatus.LOADED
    metadata: Dict[str, Any] = field(default_factory=dict)
    hooks: Dict[str, List[HookHandler]] = field(default_factory=lambda: defaultdict(list))


class PluginManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._plugins: Dict[str, Plugin] = {}
        self._hooks: Dict[str, List[HookHandler]] = defaultdict(list)

    def register(self, plugin: Plugin) -> None:
        with self._lock:
            self._plugins[plugin.name] = plugin
            for hook_name, handlers in plugin.hooks.items():
                self._hooks[hook_name].extend(handlers)

    def unregister(self, name: str) -> None:
        with self._lock:
            plugin = self._plugins.pop(name, None)
            if plugin:
                for hook_name in plugin.hooks:
                    self._hooks[hook_name] = [
                        h for h in self._hooks[hook_name] if h not in plugin.hooks[hook_name]
                    ]

    def get(self, name: str) -> Optional[Plugin]:
        return self._plugins.get(name)

    def activate(self, name: str) -> None:
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin:
                plugin.status = PluginStatus.ACTIVE

    def disable(self, name: str) -> None:
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin:
                plugin.status = PluginStatus.DISABLED

    def hook(self, name: str, *args: Any, **kwargs: Any) -> List[Any]:
        results: List[Any] = []
        with self._lock:
            handlers = list(self._hooks.get(name, []))
        for handler in handlers:
            try:
                results.append(handler(*args, **kwargs))
            except Exception:
                continue
        return results

    def list_plugins(self) -> List[str]:
        with self._lock:
            return list(self._plugins.keys())
