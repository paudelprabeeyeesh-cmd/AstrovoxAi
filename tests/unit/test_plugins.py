"""Tests for plugin SDK."""

from __future__ import annotations

import sys
import types

import pytest

from astrovox.plugins import PluginContext, PluginSDK, PluginManifest


def test_plugin_context_emits_event():
    sdk = PluginSDK()
    received = []
    sdk.event_bus.subscribe("test", lambda e: received.append(e.name))
    ctx = PluginContext(manifest=PluginManifest(name="p", version="0.1.0", entry="p"), event_bus=sdk.event_bus)
    ctx.emit("test")
    assert received == ["test"]


def test_plugin_context_ensure_permission_raises_when_missing():
    sdk = PluginSDK()
    ctx = PluginContext(manifest=PluginManifest(name="p", version="0.1.0", entry="p", permissions=[]), event_bus=sdk.event_bus)
    with pytest.raises(Exception):
        ctx.ensure_permission("network")


def test_plugin_sdk_register_and_unregister():
    sdk = PluginSDK()
    manifest = PluginManifest(name="p", version="0.1.0", entry="p")
    ctx = PluginContext(manifest=manifest, event_bus=sdk.event_bus)
    plugin = type("P", (), {"manifest": manifest, "context": ctx, "load": lambda self: None, "unload": lambda self: None})()
    sdk.register(plugin)
    assert "p" in sdk._plugins
    sdk.unregister("p")
    assert "p" not in sdk._plugins
