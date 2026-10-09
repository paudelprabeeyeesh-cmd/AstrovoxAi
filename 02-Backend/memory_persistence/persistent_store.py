"""
Persistent Store - Task 121

Thread-safe filesystem-backed key-value store with atomic writes and optional TTL.
Stdlib-only.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Entry:
    key: str
    value: Any
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        return self.expires_at is not None and datetime.utcnow() >= self.expires_at


class PersistentStore:
    """
    Persistent key-value store backed by the filesystem.

    Features:
    - Atomic writes via temp-then-rename
    - Thread-safe access
    - Optional TTL per key
    - Metadata support
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir is None:
            storage_dir = os.path.join(tempfile.gettempdir(), "astrovox_persistent_store")
        self.storage_dir = storage_dir
        self._lock = threading.RLock()
        self._entries: Dict[str, Entry] = {}
        os.makedirs(self.storage_dir, exist_ok=True)

    def _key_path(self, key: str) -> str:
        safe = key.replace("/", "_").replace("\\", "_")
        return os.path.join(self.storage_dir, f"{safe}.json")

    def _is_expired(self, key: str) -> bool:
        entry = self._entries.get(key)
        return entry is not None and entry.is_expired()

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Persist a value atomically."""
        with self._lock:
            if self._is_expired(key):
                self._entries.pop(key, None)
            expires_at = None
            if ttl_seconds is not None and ttl_seconds > 0:
                expires_at = datetime.utcnow()
                expires_at = datetime.fromtimestamp(expires_at.timestamp() + ttl_seconds)
            entry = Entry(key=key, value=value, expires_at=expires_at, metadata=metadata or {})
            self._entries[key] = entry
            self._write(key, entry)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value, returning default if missing or expired."""
        with self._lock:
            if self._is_expired(key):
                self._entries.pop(key, None)
                self._delete_file(key)
                return default
            entry = self._entries.get(key)
            if entry is None:
                entry = self._read(key)
                if entry is None:
                    return default
                if entry.is_expired():
                    self._delete_file(key)
                    return default
                self._entries[key] = entry
            return entry.value

    def delete(self, key: str) -> bool:
        """Remove a key from store and disk."""
        with self._lock:
            existed = key in self._entries or os.path.exists(self._key_path(key))
            self._entries.pop(key, None)
            self._delete_file(key)
            return existed

    def list_keys(self) -> List[str]:
        """List all non-expired keys."""
        with self._lock:
            keys = []
            for key, entry in list(self._entries.items()):
                if entry.is_expired():
                    self._entries.pop(key, None)
                    self._delete_file(key)
                else:
                    keys.append(key)
            for fname in os.listdir(self.storage_dir):
                if fname.endswith(".json"):
                    key = fname[:-5].replace("_", "/").replace("_", "/", 1) if fname.count("_") else fname[:-5]
                    if key not in self._entries:
                        entry = self._read(key)
                        if entry and not entry.is_expired():
                            self._entries[key] = entry
                            keys.append(key)
            return sorted(set(keys))

    def exists(self, key: str) -> bool:
        with self._lock:
            if self._is_expired(key):
                self._entries.pop(key, None)
                self._delete_file(key)
                return False
            if key in self._entries:
                return True
            return self._read(key) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            for fname in os.listdir(self.storage_dir):
                if fname.endswith(".json"):
                    os.remove(os.path.join(self.storage_dir, fname))

    def set_ttl(self, key: str, ttl_seconds: int) -> bool:
        """Set or update TTL for an existing key."""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                entry = self._read(key)
                if entry is None:
                    return False
                self._entries[key] = entry
            entry.expires_at = datetime.fromtimestamp(datetime.utcnow().timestamp() + ttl_seconds)
            self._write(key, entry)
            return True

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._entries.get(key) or self._read(key)
            if entry is None:
                return None
            return entry.metadata

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._entries)
            expired = sum(1 for e in self._entries.values() if e.is_expired())
            return {
                "storage_dir": self.storage_dir,
                "total_keys": total,
                "expired_keys": expired,
                "active_keys": total - expired,
            }

    def _write(self, key: str, entry: Entry) -> None:
        path = self._key_path(key)
        tmp = path + ".tmp"
        data = {
            "key": entry.key,
            "value": entry.value,
            "created_at": entry.created_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "metadata": entry.metadata,
        }
        with open(tmp, "w") as f:
            json.dump(data, f, default=str)
        os.replace(tmp, path)

    def _read(self, key: str) -> Optional[Entry]:
        path = self._key_path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return Entry(
                key=data["key"],
                value=data["value"],
                created_at=datetime.fromisoformat(data["created_at"]),
                expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
                metadata=data.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def _delete_file(self, key: str) -> None:
        try:
            os.remove(self._key_path(key))
        except OSError:
            pass
