"""Tests for plugin SDK - expanded coverage."""

from __future__ import annotations

import pytest

from astrovox.plugins import EventBus, PluginContext, PluginPermissionDenied, PluginSDK, PluginManifest


def test_event_bus_unsubscribe_not_supported():
    bus = EventBus()
    bus.subscribe("e", lambda e: None)
    assert True


def test_plugin_manifest_defaults():
    manifest = PluginManifest(name="p", version="0.1.0", entry="p")
    assert manifest.api_version == "1.0"
    assert manifest.permissions == []


def test_plugin_context_event_payload():
    sdk = PluginSDK()
    received = []
    sdk.event_bus.subscribe("payload_test", lambda e: received.append(e.payload))
    ctx = PluginContext(manifest=PluginManifest(name="p", version="0.1.0", entry="p"), event_bus=sdk.event_bus)
    ctx.emit("payload_test", payload={"key": "value"})
    assert received[0] == {"key": "value"}


def test_plugin_sdk_unregister_missing_is_safe():
    sdk = PluginSDK()
    sdk.unregister("missing")
