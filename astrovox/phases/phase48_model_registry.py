"""Model registry for Astrovox."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class ModelRecord:
    """A model registry entry."""
    id: str
    name: str
    version: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    created: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "version": self.version,
                "description": self.description, "tags": self.tags, "metadata": self.metadata}


class ModelRegistry:
    """Model catalog with metadata."""

    def __init__(self):
        self.models: dict[str, ModelRecord] = {}

    def register(self, name: str, version: str, description: str = "",
                 tags: list[str] | None = None, metadata: dict | None = None) -> ModelRecord:
        model_id = f"m_{len(self.models)}"
        rec = ModelRecord(id=model_id, name=name, version=version, description=description,
                          tags=list(tags or []), metadata=dict(metadata or {}))
        self.models[model_id] = rec
        return rec

    def get(self, model_id: str) -> ModelRecord | None:
        return self.models.get(model_id)

    def list_models(self, name: str | None = None) -> list[ModelRecord]:
        if name is None:
            return list(self.models.values())
        return [m for m in self.models.values() if m.name == name]

    def search(self, query: str) -> list[ModelRecord]:
        q = query.lower()
        return [m for m in self.models.values()
                if q in m.name.lower() or q in m.description.lower() or q in " ".join(m.tags).lower()]

    def delete(self, model_id: str) -> bool:
        if model_id in self.models:
            del self.models[model_id]
            return True
        return False

    def count(self) -> int:
        return len(self.models)
