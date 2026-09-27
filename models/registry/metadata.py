import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ModelMetadata:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "metadata": self._data,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> "ModelMetadata":
        data = json.loads(path.read_text())
        instance = cls(data["name"], data["version"])
        instance._data = data.get("metadata", {})
        return instance
