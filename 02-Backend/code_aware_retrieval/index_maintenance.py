import hashlib
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

import numpy as np


@dataclass
class FileEvent:
    path: str
    event_type: str
    content_hash: Optional[str] = None


class IndexMaintenance:
    def __init__(self, parser: Any) -> None:
        self._parser = parser
        self._index: Dict[str, Any] = {}
        self._hashes: Dict[str, str] = {}
        self._dirty: Set[str] = set()
        self._lock = threading.Lock()
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _hash_content(self, path: str, content: str) -> str:
        return hashlib.sha256(f"{path}:{content}".encode()).hexdigest()

    def on_file_event(self, event: FileEvent) -> None:
        with self._lock:
            self._dirty.add(event.path)
            if event.content_hash:
                self._hashes[event.path] = event.content_hash

    def incremental_reindex(self) -> int:
        with self._lock:
            dirty = list(self._dirty)
            self._dirty.clear()
        count = 0
        for path in dirty:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                new_hash = self._hash_content(path, content)
                old_hash = self._hashes.get(path)
                if new_hash != old_hash:
                    parsed = self._parser.parse(path, content)
                    self._index[path] = parsed
                    self._hashes[path] = new_hash
                    count += 1
            except OSError:
                pass
        return count

    def full_reindex(self, files: List[str]) -> int:
        count = 0
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                parsed = self._parser.parse(path, content)
                self._index[path] = parsed
                self._hashes[path] = self._hash_content(path, content)
                count += 1
            except OSError:
                pass
        with self._lock:
            self._dirty.clear()
        return count

    def consistency_check(self) -> Dict[str, Any]:
        with self._lock:
            indexed = set(self._index.keys())
            hashed = set(self._hashes.keys())
        result: Dict[str, Any] = {
            "indexed_files": len(indexed),
            "hashed_files": len(hashed),
            "in_index_not_hashed": list(indexed - hashed),
            "in_hash_not_indexed": list(hashed - indexed),
            "consistent": indexed == hashed,
        }
        return result

    def get_index_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_files": len(self._index),
                "dirty_files": len(self._dirty),
                "hashes": len(self._hashes),
            }
