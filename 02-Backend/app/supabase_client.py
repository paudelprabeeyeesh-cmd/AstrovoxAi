"""Shared Supabase client.

Provides a single, lazily-created Supabase client reused across the backend
instead of constructing a new client on every request/module import.
"""
import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a cached Supabase client, creating it on first use."""
    url = os.getenv("VITE_SUPABASE_URL")
    key = os.getenv("VITE_SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured")
    return create_client(url, key)
