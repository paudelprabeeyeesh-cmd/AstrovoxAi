"""AI plugin system."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AIPlugin:
    plugin_id: str
    name: str
    version: str
    entrypoint: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIPluginSystem:
    def __init__(self) -> None:
        self._plugins: Dict[str, AIPlugin] = {}

    def register(self, plugin: AIPlugin) -> None:
        self._plugins[plugin.plugin_id] = plugin

    def load(self, plugin_id: str) -> Optional[AIPlugin]:
        return self._plugins.get(plugin_id)


ai_plugin_system = AIPluginSystem()
