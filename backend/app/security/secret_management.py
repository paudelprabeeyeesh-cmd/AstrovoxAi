"""Secret management with encrypted vault and rotation."""
import os
import time
import json
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from .encryption import EncryptionService

logger = logging.getLogger(__name__)


@dataclass
class SecretMetadata:
    key: str
    version: int
    created_at: float
    expires_at: Optional[float]
    tags: List[str] = field(default_factory=list)


class SecretVault:
    def __init__(self, encryption_service: Optional[EncryptionService] = None):
        self._encryption = encryption_service or EncryptionService()
        self._store: Dict[str, Dict[int, str]] = {}
        self._meta: Dict[str, SecretMetadata] = {}
        self._lock = __import__('threading').Lock()

    def put(self, key: str, value: str, tags: List[str] = None, ttl: Optional[int] = None) -> SecretMetadata:
        with self._lock:
            if key not in self._store:
                self._store[key] = {}
                self._meta[key] = SecretMetadata(key=key, version=0, created_at=time.time(), expires_at=None, tags=tags or [])
            version = len(self._store[key]) + 1
            self._store[key][version] = self._encryption.encrypt(value)
            meta = self._meta[key]
            meta.version = version
            meta.created_at = time.time()
            meta.expires_at = time.time() + ttl if ttl else None
            if tags:
                meta.tags = tags
            return meta

    def get(self, key: str, version: Optional[int] = None) -> Optional[str]:
        with self._lock:
            versions = self._store.get(key)
            if not versions:
                return None
            ver = version or max(versions.keys())
            encrypted = versions.get(ver)
            if not encrypted:
                return None
            try:
                return self._encryption.decrypt(encrypted)
            except Exception:
                return None

    def rotate(self, key: str, new_value: str, tags: List[str] = None) -> SecretMetadata:
        return self.put(key, new_value, tags=tags)

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        with self._lock:
            versions = self._store.get(key)
            if not versions:
                return False
            if version:
                if version in versions:
                    del versions[version]
                    return True
                return False
            del self._store[key]
            del self._meta[key]
            return True

    def list_keys(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def get_metadata(self, key: str) -> Optional[SecretMetadata]:
        with self._lock:
            return self._meta.get(key)


class SecretRotation:
    def __init__(self, vault: Optional[SecretVault] = None):
        self._vault = vault or SecretVault()

    def rotate_if_needed(self, key: str, max_age: int = 86400) -> bool:
        meta = self._vault.get_metadata(key)
        if not meta:
            return False
        if time.time() - meta.created_at > max_age:
            logger.info("Rotating secret %s due to age", key)
            return True
        return False


secret_vault = SecretVault()
secret_rotation = SecretRotation(secret_vault)
