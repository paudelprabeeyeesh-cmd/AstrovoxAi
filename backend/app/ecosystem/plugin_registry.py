from dataclasses import dataclass, field
from typing import Dict, List, Any
import uuid


@dataclass
class Plugin:
    plugin_id: str
    name: str
    version: str
    capabilities: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.plugin_id:
            self.plugin_id = str(uuid.uuid4())


class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        self.plugins[plugin.plugin_id] = plugin

    def discover(self, capability: str) -> List[Plugin]:
        return [p for p in self.plugins.values() if capability in p.capabilities]
