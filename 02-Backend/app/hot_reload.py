"""Hot reload support for development."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

_watchers: Dict[str, List[Callable[[str], None]]] = {}
_observer: Optional[Observer] = None
_watched_paths: Set[str] = set()


class HotReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            path = event.src_path
            for callback in _watchers.get(path, []):
                callback(path)


class HotReloadManager:
    _initialized = False

    @classmethod
    def initialize(cls, watch_paths: Optional[List[str]] = None) -> None:
        global _observer
        if cls._initialized:
            return
        paths = watch_paths or [str(Path(__file__).parent)]
        handler = HotReloadHandler()
        _observer = Observer()
        for path in paths:
            if path not in _watched_paths:
                _observer.schedule(handler, path, recursive=True)
                _watched_paths.add(path)
        _observer.start()
        cls._initialized = True

    @classmethod
    def watch(cls, path: str, callback: Callable[[str], None]) -> None:
        if path not in _watchers:
            _watchers[path] = []
        _watchers[path].append(callback)

    @classmethod
    def stop(cls) -> None:
        global _observer
        if _observer:
            _observer.stop()
            _observer.join()
            cls._initialized = False


def hot_reload_enabled() -> bool:
    return os.getenv("HOT_RELOAD", "false").lower() == "true"
