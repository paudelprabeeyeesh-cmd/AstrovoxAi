"""Marketplace plugin registry."""

import importlib.util
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class MarketplacePlugin:
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str
    manifest: dict
    installs: int = 0
    rating: float = 0.0
    verified: bool = False


class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, MarketplacePlugin] = {}

    def register_plugin(self, name: str, version: str, description: str, author: str, category: str, manifest: dict) -> MarketplacePlugin:
        plugin_id = str(uuid.uuid4())
        plugin = MarketplacePlugin(
            id=plugin_id,
            name=name,
            version=version,
            description=description,
            author=author,
            category=category,
            manifest=manifest,
        )
        self._plugins[plugin_id] = plugin
        self._persist(plugin)
        return plugin

    def _persist(self, plugin: MarketplacePlugin):
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO marketplace_plugins (id, name, version, description, author, category, manifest, installs, rating, verified) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    plugin.id,
                    plugin.name,
                    plugin.version,
                    plugin.description,
                    plugin.author,
                    plugin.category,
                    json.dumps(plugin.manifest),
                    plugin.installs,
                    plugin.rating,
                    1 if plugin.verified else 0,
                ),
            )
            conn.commit()

    def list_plugins(self, category: Optional[str] = None, verified_only: bool = False) -> list[dict]:
        plugins = list(self._plugins.values())
        if category:
            plugins = [p for p in plugins if p.category == category]
        if verified_only:
            plugins = [p for p in plugins if p.verified]
        return [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "category": p.category,
                "installs": p.installs,
                "rating": p.rating,
                "verified": p.verified,
            }
            for p in plugins
        ]

    def install_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.installs += 1
        self._persist(plugin)
        return True

    def uninstall_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return False
        plugin.installs = max(0, plugin.installs - 1)
        self._persist(plugin)
        return True


plugin_registry = PluginRegistry()
