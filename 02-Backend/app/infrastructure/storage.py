"""Storage abstraction layer."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import BinaryIO, Dict, Optional

from app.core.config import get_config

logger = logging.getLogger(__name__)


class Storage:
    """File storage abstraction with local filesystem backend."""

    def __init__(self, base_path: Optional[str] = None) -> None:
        self._config = get_config()
        self._base_path = Path(base_path or os.getenv("STORAGE_PATH", "./storage"))
        self._base_path.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, metadata: Optional[Dict[str, str]] = None) -> str:
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        path = self._base_path / key_hash
        path.write_bytes(data)
        logger.info(f"Stored object: {key} -> {key_hash}")
        return key_hash

    def get(self, key: str) -> Optional[bytes]:
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        path = self._base_path / key_hash
        if not path.exists():
            return None
        return path.read_bytes()

    def delete(self, key: str) -> bool:
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        path = self._base_path / key_hash
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, key: str) -> bool:
        key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
        return (self._base_path / key_hash).exists()

    def list_keys(self, prefix: str = "") -> list[str]:
        keys = []
        for path in self._base_path.iterdir():
            if path.is_file():
                keys.append(path.name)
        return keys


_storage = Storage()


def get_storage() -> Storage:
    return _storage
