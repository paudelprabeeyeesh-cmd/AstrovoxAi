"""Enhanced secret vault with rotation and access logging."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Secret:
    key: str
    value: str
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    rotated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecretAccess:
    key: str
    accessed_by: str
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = "read"


class SecretVault:
    def __init__(self) -> None:
        self._secrets: Dict[str, Secret] = {}
        self._access_log: List[SecretAccess] = []

    def put(self, key: str, value: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        existing = self._secrets.get(key)
        version = (existing.version + 1) if existing else 1
        self._secrets[key] = Secret(key=key, value=value, version=version, metadata=metadata or {})
        logger.info("Stored secret %s v%d", key, version)

    def get(self, key: str, accessed_by: str = "system") -> Optional[Secret]:
        secret = self._secrets.get(key)
        if secret:
            self._access_log.append(SecretAccess(key=key, accessed_by=accessed_by))
        return secret

    def rotate(self, key: str, new_value: str) -> Optional[Secret]:
        secret = self._secrets.get(key)
        if not secret:
            return None
        secret.value = new_value
        secret.version += 1
        secret.rotated_at = datetime.now(timezone.utc)
        logger.info("Rotated secret %s to v%d", key, secret.version)
        return secret

    def delete(self, key: str) -> None:
        self._secrets.pop(key, None)

    def list_keys(self) -> List[str]:
        return list(self._secrets.keys())

    def access_history(self, key: str, limit: int = 50) -> List[Dict[str, Any]]:
        history = [a for a in self._access_log if a.key == key][-limit:]
        return [
            {
                "key": a.key,
                "accessed_by": a.accessed_by,
                "action": a.action,
                "accessed_at": a.accessed_at.isoformat(),
            }
            for a in history
        ]


secret_vault = SecretVault()
