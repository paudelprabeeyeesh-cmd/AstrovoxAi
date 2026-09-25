from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    description: str
    author: str
    tags: List[str] = field(default_factory=list)
    entrypoint: str = "plugin.py"
    schema_version: str = "1.0"
    dependencies: Dict[str, str] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "tags": self.tags,
            "entrypoint": self.entrypoint,
            "schema_version": self.schema_version,
            "dependencies": self.dependencies,
            "config": self.config,
        }


@dataclass
class PluginRecord:
    manifest: PluginManifest
    installed_at: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True
    path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
