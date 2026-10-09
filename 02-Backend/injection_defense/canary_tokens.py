"""Canary Tokens: embed secret strings and detect if they leak in output."""

from __future__ import annotations

import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional


_DEFAULT_PREFIX = "ASTROVOX-CANARY-2026-001"
_CANARY_REGEX = re.compile(r"ASTROVOX-CANARY-2026-001-[A-F0-9]{1,12}-[0-9]{3,}", re.IGNORECASE)
_CANARY_REGEX_LEAKAGE = re.compile(
    r"(?i)(ASTROVOX-CANARY|canary|token|secret|key).{0,50}(ASTROVOX-CANARY-2026-001-[A-F0-9]{1,12}-[0-9]{3,})",
    re.IGNORECASE,
)
_UNICODE_WS = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]+")
_HOMOGLYPHS = re.compile(r"[A-Za-z0-9]+", re.ASCII)


def _normalize_for_canary(text: str) -> str:
    normalized = text
    normalized = _UNICODE_WS.sub("", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _normalize_homoglyphs(text: str) -> str:
    return re.sub(r"[^A-Z0-9-]", "", text.upper())


def _is_canary_like(value: str) -> bool:
    if not value or len(value) < 10:
        return False
    if not value.startswith(_DEFAULT_PREFIX):
        return False
    return bool(_CANARY_REGEX.match(value))


@dataclass
class CanaryToken:
    value: str
    created_at: float = field(default_factory=time.time)
    used: bool = False
    expires_at: Optional[float] = None
    max_uses: int = 1
    use_count: int = 0

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def is_consumed(self) -> bool:
        return self.use_count >= self.max_uses

    def mark_used(self) -> None:
        self.used = True
        self.use_count += 1


class CanaryRegistry:
    def __init__(self) -> None:
        self._tokens: dict[str, CanaryToken] = {}
        self._revoked: set[str] = set()

    def generate(self, ttl_seconds: Optional[float] = None, max_uses: int = 1) -> CanaryToken:
        hex_ = secrets.token_hex(6).upper()[:secrets.randbelow(12) + 1]
        suffix = f"{secrets.randbelow(10)}{secrets.randbelow(10)}{secrets.randbelow(10)}"
        raw = f"{_DEFAULT_PREFIX}-{hex_}-{suffix}"
        expires = time.time() + ttl_seconds if ttl_seconds else None
        token = CanaryToken(value=raw, expires_at=expires, max_uses=max_uses)
        canonical = raw.upper()
        self._tokens[canonical] = token
        return token

    def check(self, text: str) -> Optional[CanaryToken]:
        normalized = _normalize_for_canary(text)
        matches = _CANARY_REGEX.findall(normalized)
        found = set()
        for match in matches:
            canonical = _normalize_homoglyphs(match)
            if canonical in found:
                continue
            found.add(canonical)
            if canonical in self._revoked:
                continue
            if canonical in self._tokens:
                token = self._tokens[canonical]
                if token.is_expired() or token.is_consumed():
                    continue
                token.mark_used()
                return token
        return None

    def is_leaked(self, text: str) -> bool:
        return self.check(text) is not None

    def revoke(self, token_value: str) -> bool:
        canonical = _normalize_homoglyphs(token_value.strip())
        if canonical in self._revoked:
            return False
        if canonical in self._tokens:
            del self._tokens[canonical]
            self._revoked.add(canonical)
            return True
        self._revoked.add(canonical)
        return False

    def cleanup_expired(self) -> int:
        expired_keys = [k for k, v in self._tokens.items() if v.is_expired() or v.is_consumed()]
        for k in expired_keys:
            del self._tokens[k]
        return len(expired_keys)

    def active_count(self) -> int:
        return sum(1 for v in self._tokens.values() if not v.is_expired() and not v.is_consumed())

    def rotate(self, token_value: str, ttl_seconds: Optional[float] = None) -> Optional[CanaryToken]:
        canonical = _normalize_homoglyphs(token_value.strip())
        if canonical in self._revoked:
            return None
        old = self._tokens.pop(canonical, None)
        if old is not None:
            old.max_uses = old.use_count
            old.max_uses = max(old.max_uses, 1)
        return self.generate(ttl_seconds=ttl_seconds)


_global_registry = CanaryRegistry()


def get_global_registry() -> CanaryRegistry:
    return _global_registry


def create_canary(ttl_seconds: Optional[float] = None, max_uses: int = 1) -> str:
    return _global_registry.generate(ttl_seconds, max_uses=max_uses).value


def check_canary(text: str) -> bool:
    return _global_registry.is_leaked(text)


def embed_canary(text: str, token: Optional[str] = None) -> str:
    if token is None:
        token = create_canary()
    return f"{text} [{token}]"
