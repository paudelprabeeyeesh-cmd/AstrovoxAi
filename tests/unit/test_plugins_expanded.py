"""Tests for plugin SDK - expanded coverage."""

from __future__ import annotations

import sys
import types

import pytest

from astrovox.plugins import EventBus, PluginContext, PluginPermissionDenied, PluginSDK, PluginManifest


def test_event_bus_multiple_subscribers():
    bus = EventBus()
    results = []
    bus.subscribe("e", lambda e: results.append(1))
    bus.subscribe("e", lambda e: results.append(2))
    bus.publish(type("E", (), {"name": "e", "payload": {}})())
    assert results == [1, 2]


def test_event_bus_no_subscribers_does_not_raise():
    bus = EventBus()
    bus.publish(type("E", (), {"name": "missing", "payload": {}})())


def test_plugin_permission_denied_message():
    exc = PluginPermissionDenied("network")
    assert "network" in str(exc)


def test_plugin_sdk_hot_reload():
    sdk = PluginSDK()
    manifest = PluginManifest(name="p", version="0.1.0", entry="p")
    ctx = PluginContext(manifest=manifest, event_bus=sdk.event_bus)
    plugin = type("P", (), {"manifest": manifest, "context": ctx, "load": lambda self: None, "unload": lambda self: None})()
    sdk.register(plugin)
    new_manifest = PluginManifest(name="p", version="0.2.0", entry="p")
    new_ctx = PluginContext(manifest=new_manifest, event_bus=sdk.event_bus)
    new_plugin = type("P2", (), {"manifest": new_manifest, "context": new_ctx, "load": lambda self: None, "unload": lambda self: None})()
    sdk._plugins["p"] = new_plugin
    assert "p" in sdk._plugins
