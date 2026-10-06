"""Secrets manager."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Secret:
    """A stored secret."""
    name: str
    value: str
    created: float = field(default_factory=lambda: time.time())
    expires: float | None = None

    def is_expired(self) -> bool:
        if self.expires is None:
            return False
        return time.time() > self.expires


class SecretManager:
    """Secrets storage."""

    def __init__(self):
        self.secrets: dict[str, Secret] = {}

    def set(self, name: str, value: str, ttl_seconds: float | None = None) -> None:
        expires = (time.time() + ttl_seconds) if ttl_seconds else None
        self.secrets[name] = Secret(name=name, value=value, expires=expires)

    def get(self, name: str) -> str | None:
        s = self.secrets.get(name)
        if s is None or s.is_expired():
            return None
        return s.value

    def delete(self, name: str) -> bool:
        if name in self.secrets:
            del self.secrets[name]
            return True
        return False

    def list_secrets(self) -> list[str]:
        return [s.name for s in self.secrets.values()]

    def rotate(self, name: str, new_value: str) -> bool:
        s = self.secrets.get(name)
        if s is None:
            return False
        s.value = new_value
        s.created = time.time()
        return True

    def count(self) -> int:
        return len(self.secrets)
