"""Dynamic configuration with hot-reload support."""

import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

_config_file = Path(__file__).parent / "dynamic_config.json"
_config: Dict[str, Any] = {}
_watchers: List[Callable[[str, Any, Any], None]] = []
_lock = threading.Lock()
_last_modified = 0.0


@dataclass
class DynamicConfig:
    key: str
    value: Any
    value_type: str = "string"
    description: str = ""


class DynamicConfigManager:
    @classmethod
    def load(cls, path: Optional[Path] = None) -> Dict[str, Any]:
        global _config, _last_modified
        path = path or _config_file
        if not path.exists():
            path.write_text(json.dumps({}, indent=2))
            return {}
        try:
            stat = path.stat()
            if stat.st_mtime > _last_modified:
                with open(path, "r") as f:
                    _config = json.load(f)
                _last_modified = stat.st_mtime
                cls._notify_watchers()
        except Exception as e:
            print(f"Failed to load dynamic config: {e}")
        return _config

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        with _lock:
            return _config.get(key, os.getenv(key.upper(), default))

    @classmethod
    def set(cls, key: str, value: Any, persist: bool = True) -> None:
        with _lock:
            _config[key] = value
            if persist:
                with open(_config_file, "w") as f:
                    json.dump(_config, f, indent=2, default=str)
        cls._notify_key(key, value)

    @classmethod
    def watch(cls, callback: Callable[[str, Any, Any], None]) -> None:
        _watchers.append(callback)

    @classmethod
    def _notify_watchers(cls) -> None:
        for watcher in _watchers:
            try:
                watcher("", _config, _config)
            except Exception:
                pass

    @classmethod
    def _notify_key(cls, key: str, value: Any) -> None:
        for watcher in _watchers:
            try:
                watcher(key, value, value)
            except Exception:
                pass


DynamicConfigManager.load()
