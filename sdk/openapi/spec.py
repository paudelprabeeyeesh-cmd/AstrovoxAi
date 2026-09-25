from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class OpenAPISpec:
    title: str = "Astrovox API"
    version: str = "1.0.0"
    paths: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "openapi": "3.1.0",
            "info": {
                "title": self.title,
                "version": self.version,
                **self.info,
            },
            "paths": self.paths,
            "components": {"schemas": self.components} if self.components else {},
            "tags": [{"name": tag} for tag in self.tags],
        }

    def save(self, path: Path) -> None:
        path.write_text(
            __import__("json").dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OpenAPISpec:
        spec = cls(
            title=data.get("info", {}).get("title", "Astrovox API"),
            version=data.get("info", {}).get("version", "1.0.0"),
            paths=data.get("paths", {}),
            components=data.get("components", {}).get("schemas", {}),
            tags=[tag.get("name", "") for tag in data.get("tags", [])],
            info=data.get("info", {}),
        )
        return spec
