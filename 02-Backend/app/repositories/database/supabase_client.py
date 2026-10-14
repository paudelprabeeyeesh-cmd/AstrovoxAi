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
except Exception:  # pragma: no cover - fallback for missing package
    Client = object  # type: ignore[assignment]
    create_client = None  # type: ignore[assignment]


class _FallbackSupabaseClient:
    def __getattr__(self, name):
        return lambda *args, **kwargs: SimpleNamespace(
            user=None, session=None, data=None
        )


@lru_cache(maxsize=1)
def get_supabase():
    """Return a cached Supabase client, creating it on first use.

    A missing or unusable configuration degrades to the no-op client above
    instead of raising, so importing the backend never depends on the
    database being reachable. Denying every authenticated call is the
    fail-closed outcome; an import-time crash also takes the health
    endpoint and the unauthenticated surface down with it.
    """
    url = os.getenv("VITE_SUPABASE_URL")
    key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_PUBLISHABLE_KEY")
    if not url or not key or create_client is None:
        return _FallbackSupabaseClient()
    return create_client(url, key)
