import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union


class ObjectStore:
    def __init__(self, root: Union[str, Path]) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index_path = self.root / ".index.json"
        self._index: Dict[str, float] = self._load_index()

    def _load_index(self) -> Dict[str, float]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text())
        return {}

    def _save_index(self) -> None:
        self._index_path.write_text(json.dumps(self._index))

    def _obj_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("\\", "_")
        return self.root / f"{safe}.json"

    def put(self, key: str, value: Any) -> Path:
        path = self._obj_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        self._index[key] = time.time()
        self._save_index()
        return path

    def get(self, key: str, default: Any = None) -> Any:
        path = self._obj_path(key)
        if not path.exists():
            return default
        return json.loads(path.read_text())

    def delete(self, key: str) -> None:
        path = self._obj_path(key)
        if path.exists():
            path.unlink()
            self._index.pop(key, None)
            self._save_index()

    def exists(self, key: str) -> bool:
        return self._obj_path(key).exists()

    def keys(self):
        return list(self._index.keys())

    def list(self) -> list:
        return list(self._index.keys())
