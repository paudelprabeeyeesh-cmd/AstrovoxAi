"""Shared Supabase client.

Provides a single, lazily-created Supabase client reused across the backend
instead of constructing a new client on every request/module import.
"""

import os
from functools import lru_cache
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

try:
    from supabase import Client, create_client
except Exception as _e:  # noqa: BLE001
    Client = object  # type: ignore[assignment]
    create_client = None  # type: ignore[assignment]


class _FallbackSupabaseClient:
    """No-op Supabase client used when credentials are not configured.

    Supports the common query builder pattern so that import-time module
    initialization does not crash the entire application.
    """

    def __init__(self):
        self.auth = _FallbackAuthClient()
        self.storage = SimpleNamespace()

    def table(self, name: str):
        return _FallbackQueryBuilder()


class _FallbackAuthClient:
    def get_user(self, token: str):
        return SimpleNamespace(user=None)


class _FallbackQueryBuilder:
    def __init__(self):
        self._filters = []
        self._orders = []
        self._range = None
        self._limit = None

    def select(self, columns: str):
        return self

    def eq(self, column: str, value):
        self._filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False):
        self._orders.append((column, desc))
        return self

    def range(self, offset: int, limit: int):
        self._range = (offset, limit)
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def insert(self, payload: dict):
        return self

    def update(self, payload: dict):
        return self

    def delete(self):
        return self

    def execute(self):
        return SimpleNamespace(data=[])


@lru_cache(maxsize=1)
def get_supabase():
    """Return a cached Supabase client, creating it on first use."""
    url = os.getenv("VITE_SUPABASE_URL")
    key = os.getenv("VITE_SUPABASE_ANON_KEY")
    if not url or not key:
        return _FallbackSupabaseClient()
    if create_client is None:
        raise RuntimeError("Supabase package not installed")
    return create_client(url, key)
