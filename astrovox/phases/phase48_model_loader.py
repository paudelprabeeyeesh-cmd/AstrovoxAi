"""Model loading pipeline for Astrovox."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LoadedModel:
    """A loaded model instance."""
    name: str
    version: str
    path: str
    config: dict = field(default_factory=dict)
    loaded_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> dict:
        return {"name": self.name, "version": self.version, "path": self.path,
                "config": self.config}


class ModelLoader:
    """Load and manage model instances."""

    def __init__(self, search_paths: list[str] | None = None):
        self.search_paths = [Path(p) for p in search_paths] if search_paths else []
        self.loaded: dict[str, LoadedModel] = {}

    def load(self, model_id: str, path: str, config: dict | None = None) -> LoadedModel:
        m = LoadedModel(name=model_id, version="1.0", path=path,
                        config=dict(config) if config else {})
        self.loaded[model_id] = m
        return m

    def load_from_cache(self, name: str, version: str = "latest") -> LoadedModel | None:
        import json
        meta_path = f"models/cache/{name}/{version}.meta.json"
        try:
            meta = json.loads(open(meta_path).read())
            return self.load(name, meta["path"], meta.get("config"))
        except Exception:
            return None

    def get(self, model_id: str) -> LoadedModel | None:
        return self.loaded.get(model_id)

    def unload(self, model_id: str) -> bool:
        if model_id in self.loaded:
            del self.loaded[model_id]
            return True
        return False

    def list_loaded(self) -> list[LoadedModel]:
        return list(self.loaded.values())

    def count(self) -> int:
        return len(self.loaded)
