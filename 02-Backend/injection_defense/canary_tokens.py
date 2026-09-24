"""Canary Tokens: embed secret strings and detect if they leak in output."""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional


_DEFAULT_PREFIX = "ASTROVOX-CANARY-2026-001"
_CANARY_REGEX = re.compile(r"ASTROVOX-CANARY-2026-001-[A-F0-9]{1,12}-[0-9]{3,}")


@dataclass
class CanaryToken:
    value: str
    created_at: float = field(default_factory=time.time)
    used: bool = False
    expires_at: Optional[float] = None

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def mark_used(self) -> None:
        self.used = True


class CanaryRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, CanaryToken] = {}

    def generate(self, ttl_seconds: Optional[float] = None) -> CanaryToken:
        hex_ = secrets.token_hex(6).upper()[:secrets.randbelow(12) + 1]
        suffix = f"{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}"
        raw = f"{_DEFAULT_PREFIX}-{hex_}-{suffix}"
        expires = time.time() + ttl_seconds if ttl_seconds else None
        token = CanaryToken(value=raw, expires_at=expires)
        self._tokens[raw] = token
        return token

    def check(self, text: str) -> Optional[CanaryToken]:
        matches = _CANARY_REGEX.findall(text)
        for match in matches:
            if match in self._tokens:
                token = self._tokens[match]
                if not token.is_expired():
                    token.mark_used()
                    return token
        return None

    def is_leaked(self, text: str) -> bool:
        return self.check(text) is not None

    def revoke(self, token_value: str) -> bool:
        if token_value in self._tokens:
            del self._tokens[token_value]
            return True
        return False

    def cleanup_expired(self) -> int:
        time.time()
        expired_keys = [k for k, v in self._tokens.items() if v.is_expired()]
        for k in expired_keys:
            del self._tokens[k]
        return len(expired_keys)

    def active_count(self) -> int:
        return sum(1 for v in self._tokens.values() if not v.is_expired())


_global_registry = CanaryRegistry()


def get_global_registry() -> CanaryRegistry:
    return _global_registry


def create_canary(ttl_seconds: Optional[float] = None) -> str:
    return _global_registry.generate(ttl_seconds).value


def check_canary(text: str) -> bool:
    return _global_registry.is_leaked(text)


def embed_canary(text: str, token: Optional[str] = None) -> str:
    if token is None:
        token = create_canary()
    return f"{text} [{token}]"
