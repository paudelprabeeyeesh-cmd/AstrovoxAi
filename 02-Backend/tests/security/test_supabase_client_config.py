"""Regression tests for Supabase client configuration handling.

Guards the fix for the defect where `get_supabase()` raised after an
unreachable `return` of the documented fallback client, so importing the
backend required live Supabase credentials.
"""

import importlib
import os
import sys

import pytest


@pytest.fixture
def clean_config(monkeypatch):
    """Remove every Supabase credential and clear the cached client.

    The modules call ``load_dotenv()`` at import time, so a credential in a
    local ``.env`` is still visible here. Both modules are re-imported under
    the stripped environment rather than merely having their cache cleared:
    ``cache_clear`` alone leaves the already-resolved client reachable, which
    made these tests pass in isolation and fail when an earlier test had
    populated the cache.

    The class identity is resolved *after* the reload, because re-importing
    the module rebinds ``_FallbackSupabaseClient`` and an earlier import in
    this test module would compare against the stale class object.
    """
    for var in (
        "VITE_SUPABASE_URL",
        "VITE_SUPABASE_ANON_KEY",
        "VITE_SUPABASE_PUBLISHABLE_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    def reload():
        """Re-import both modules against the stripped environment."""
        for name in (
            "app.supabase_client",
            "app.repositories.database.supabase_client",
        ):
            sys.modules.pop(name, None)
        shared = importlib.import_module("app.supabase_client")
        repo = importlib.import_module("app.repositories.database.supabase_client")
        return shared, repo

    shared, repo = reload()
    for module in (shared, repo):
        if hasattr(module, "get_supabase"):
            module.get_supabase.cache_clear()

    yield reload

    reload()


def test_get_supabase_falls_back_when_unconfigured(clean_config):
    """An unconfigured deployment must import, not raise.

    The fallback denies authenticated access (fail-closed) instead of
    crashing the process at import time.
    """
    shared, _repo = clean_config()
    client = shared.get_supabase()
    assert isinstance(client, shared._FallbackSupabaseClient)
    # Fail-closed: an unconfigured client resolves no user.
    assert client.auth.get_user("any-token").user is None


def test_repo_get_supabase_falls_back_when_unconfigured(clean_config):
    """The repository-layer duplicate must agree with the shared one."""
    _shared, repo = clean_config()
    client = repo.get_supabase()
    assert isinstance(client, repo._FallbackSupabaseClient)


def test_fallback_query_builder_returns_no_rows(clean_config):
    """Every table read on an unconfigured client yields no rows."""
    shared, _repo = clean_config()

    result = shared.get_supabase().table("profiles").select("*").eq("id", "x").execute()
    assert result.data == []


def test_configured_credentials_are_used(monkeypatch):
    """With credentials present the real client factory is called.

    The module is imported fresh so ``load_dotenv`` runs with the credentials
    visible; importing it here would otherwise pick up a cached accessor.
    """
    calls = {}
    import importlib

    import app.supabase_client as mod

    monkeypatch.setenv("VITE_SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("VITE_SUPABASE_ANON_KEY", "dummy-key")
    sys.modules.pop("app.supabase_client", None)
    mod = importlib.import_module("app.supabase_client")
    mod.get_supabase.cache_clear()

    original = mod.create_client

    def fake_create(url, key):
        calls["url"] = url
        calls["key"] = key
        return "REAL_CLIENT"

    monkeypatch.setattr(mod, "create_client", fake_create)
    try:
        assert mod.get_supabase() == "REAL_CLIENT"
        assert calls["url"] == "http://localhost:54321"
        assert calls["key"] == "dummy-key"
    finally:
        monkeypatch.setattr(mod, "create_client", original)
        sys.modules.pop("app.supabase_client", None)
