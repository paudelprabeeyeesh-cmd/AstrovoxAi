"""Universal Lookup Engine — common interface for querying multiple providers."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class LookupProvider:
    name: str
    search: Callable[[str, Optional[Dict[str, Any]]], List[Dict[str, Any]]]
    get: Callable[[str], Optional[Dict[str, Any]]]
    list_index: Callable[[], List[str]]
    supports_incremental: bool = False
    supports_semantic: bool = False


@dataclass
class LookupResult:
    provider: str
    score: float
    item: Dict[str, Any]
    cached: bool = False


class LookupPermission:
    READ_DOCS = "docs:read"
    READ_API_SPEC = "api:read"
    READ_PLUGINS = "plugins:read"
    READ_WORKFLOWS = "workflows:read"
    READ_KNOWLEDGE = "knowledge:read"


class UniversalLookupEngine:
    """Query multiple lookup providers through a common interface."""

    def __init__(self, default_ttl: float = 60.0) -> None:
        self._providers: Dict[str, LookupProvider] = {}
        self._cache: Dict[str, LookupResult] = {}
        self._cache_ttl: Dict[str, float] = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._permissions: List[str] = []

    def register_provider(self, provider: LookupProvider) -> None:
        self._providers[provider.name] = provider

    def set_permissions(self, permissions: List[str]) -> None:
        self._permissions = list(permissions)

    def search(
        self,
        query: str,
        *,
        providers: Optional[List[str]] = None,
        max_results: int = 20,
        permission_filter: Optional[List[str]] = None,
        semantic: bool = False,
    ) -> List[LookupResult]:
        self._evict_expired()
        candidates = providers or list(self._providers.keys())
        allowed = permission_filter or self._permissions
        results: List[LookupResult] = []

        for provider_name in candidates:
            provider = self._providers.get(provider_name)
            if not provider:
                continue
            if provider.supports_semantic and semantic:
                raw = provider.search(query, {"mode": "semantic", "permissions": allowed})
            else:
                raw = provider.search(query, {"permissions": allowed})
            for item in raw:
                score = self._score_item(query, item)
                results.append(LookupResult(provider=provider_name, score=score, item=item))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:max_results]

    def get(self, provider_name: str, key: str) -> Optional[Dict[str, Any]]:
        self._evict_expired()
        provider = self._providers.get(provider_name)
        if not provider:
            return None
        return provider.get(key)

    def _evict_expired(self) -> None:
        now_ts = now()
        with self._lock:
            expired = [cache_key for cache_key, ts in self._cache_ttl.items() if now_ts > ts]
            for cache_key in expired:
                self._cache.pop(cache_key, None)
                self._cache_ttl.pop(cache_key, None)

    def incremental_index(self, provider_name: str, changed_keys: List[str]) -> None:
        provider = self._providers.get(provider_name)
        if not provider or not provider.supports_incremental:
            return
        self._invalidate_cache(provider_name, changed_keys)

    def clear_cache(self, provider_name: Optional[str] = None) -> None:
        with self._lock:
            if provider_name:
                keys = [k for k in self._cache if k.startswith(f"{provider_name}:")]
                for key in keys:
                    self._cache.pop(key, None)
                    self._cache_ttl.pop(key, None)
            else:
                self._cache.clear()
                self._cache_ttl.clear()

    def _score_item(self, query: str, item: Dict[str, Any]) -> float:
        haystack = " ".join(str(value) for value in item.values()).lower()
        query_lower = query.lower()
        if query_lower == haystack:
            return 1.0
        if query_lower in haystack:
            return 0.8
        query_terms = query_lower.split()
        matches = sum(1 for term in query_terms if term in haystack)
        return max(0.1, matches / max(len(query_terms), 1)) if query_terms else 0.0

    def _invalidate_cache(self, provider_name: str, changed_keys: List[str]) -> None:
        with self._lock:
            for key in changed_keys:
                cache_key = f"{provider_name}:{key}"
                self._cache.pop(cache_key, None)
                self._cache_ttl.pop(cache_key, None)


_lookup_engine = UniversalLookupEngine()


def get_lookup_engine() -> UniversalLookupEngine:
    return _lookup_engine
