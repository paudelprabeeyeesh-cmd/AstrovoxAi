"""Tests for the plugin manager (Stage 22 step 2)."""

from __future__ import annotations

import os
import tempfile
import unittest

from app.ecosystem.manager import (
    HookBus,
    PluginManager,
    PluginSandbox,
    PluginStorage,
)
from app.ecosystem.plugins import (
    PluginLifecycleError,
    PluginManifest,
    PluginPermission,
    PluginState,
    satisfies_range,
)


class HookBusTest(unittest.TestCase):
    def test_subscribe_emit(self):
        bus = HookBus()
        received = []
        bus.subscribe("event", lambda x: received.append(x))
        bus.emit("event", "hello")
        self.assertEqual(received, ["hello"])

    def test_emit_isolates_handler_errors(self):
        bus = HookBus()
        bus.subscribe("event", lambda x: 1 / 0)
        good = []
        bus.subscribe("event", lambda x: good.append(x))
        bus.emit("event", "value")
        self.assertEqual(good, ["value"])

    def test_unsubscribe(self):
        bus = HookBus()
        h = lambda x: None
        bus.subscribe("event", h)
        bus.unsubscribe("event", h)
        self.assertEqual(bus.emit("event", 1), [])


class PluginSandboxTest(unittest.TestCase):
    def test_grant_and_require(self):
        sandbox = PluginSandbox()
        sandbox.grant(["memory:read"])
        self.assertTrue(sandbox.has("memory:read"))
        sandbox.require("memory:read")

    def test_require_ungranted_raises(self):
        sandbox = PluginSandbox()
        with self.assertRaises(PluginLifecycleError):
            sandbox.require("network:outgoing")

    def test_register_and_call(self):
        sandbox = PluginSandbox()
        sandbox.register("echo", lambda x: x * 2)
        self.assertEqual(sandbox.call("echo", 5), 10)

    def test_unknown_call_raises(self):
        sandbox = PluginSandbox()
        with self.assertRaises(PluginLifecycleError):
            sandbox.call("missing")


class PluginStorageTest(unittest.TestCase):
    def test_write_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = PluginStorage(base_dir=tmp)
            storage.write("plugin1", {"key": "value"})
            self.assertEqual(storage.read("plugin1"), {"key": "value"})

    def test_read_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = PluginStorage(base_dir=tmp)
            self.assertEqual(storage.read("missing"), {})

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            storage = PluginStorage(base_dir=tmp)
            storage.write("p", {"a": 1})
            storage.delete("p")
            self.assertEqual(storage.read("p"), {})


class PluginManagerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["ASTROVOX_PLUGINS_DIR"] = os.path.join(self.tmp, "plugins")
        os.environ["ASTROVOX_PLUGIN_STORAGE"] = os.path.join(self.tmp, "store")
        from app.ecosystem import manager as mgr_mod
        mgr_mod._GLOBAL_MANAGER = None

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_install_and_enable(self):
        manager = PluginManager()
        manifest = PluginManifest(
            id="github", name="GitHub", version="1.0.0",
            entry_point="github:Plugin", permissions=["network:outgoing"],
        )
        record = manager.install(manifest)
        self.assertEqual(record.state, PluginState.INSTALLED)
        manager.enable("github")
        record = manager.registry.get("github")
        self.assertEqual(record.state, PluginState.ENABLED)

    def test_install_validates_permissions(self):
        manager = PluginManager()
        manifest = PluginManifest(
            id="x", name="X", version="1.0.0",
            entry_point="x:X", permissions=["made:up"],
        )
        with self.assertRaises(PluginLifecycleError):
            manager.install(manifest)

    def test_install_validates_platform_version(self):
        manager = PluginManager(host_version="1.0.0")
        manifest = PluginManifest(
            id="x", name="X", version="1.0.0",
            entry_point="x:X", min_platform_version="2.0.0",
        )
        with self.assertRaises(PluginLifecycleError):
            manager.install(manifest)

    def test_install_validates_dependencies(self):
        manager = PluginManager()
        manifest = PluginManifest(
            id="x", name="X", version="1.0.0",
            entry_point="x:X", dependencies={"missing": ">=1.0.0"},
        )
        with self.assertRaises(PluginLifecycleError):
            manager.install(manifest)

    def test_disable_and_uninstall(self):
        manager = PluginManager()
        manifest = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:X")
        manager.install(manifest)
        manager.enable("x")
        manager.disable("x")
        self.assertEqual(manager.registry.get("x").state, PluginState.DISABLED)
        manager.uninstall("x")
        self.assertIsNone(manager.registry.get("x"))

    def test_update(self):
        manager = PluginManager()
        manifest = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:X")
        manager.install(manifest)
        manager.update("x", "2.0.0")
        self.assertEqual(manager.registry.get("x").manifest.version, "2.0.0")

    def test_set_config(self):
        manager = PluginManager()
        manifest = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:X")
        manager.install(manifest)
        manager.set_config("x", {"key": "value"})
        self.assertEqual(manager.registry.get("x").config["key"], "value")

    def test_grant_revoke(self):
        manager = PluginManager()
        manifest = PluginManifest(
            id="x", name="X", version="1.0.0",
            entry_point="x:X", permissions=["memory:read"],
        )
        manager.install(manifest)
        manager.grant("x", ["memory:write"])
        self.assertIn("memory:write", manager.registry.get("x").granted_permissions)
        manager.revoke("x", ["memory:write"])
        self.assertNotIn("memory:write", manager.registry.get("x").granted_permissions)

    def test_grant_invalid_permission(self):
        manager = PluginManager()
        manifest = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:X")
        manager.install(manifest)
        with self.assertRaises(PluginLifecycleError):
            manager.grant("x", ["bad:perm"])

    def test_resolve_dependencies_missing(self):
        manager = PluginManager()
        manifest = PluginManifest(
            id="x", name="X", version="1.0.0",
            entry_point="x:X", dependencies={"missing": ">=1.0.0"},
        )
        missing = manager.resolve_dependencies(manifest)
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0][0], "missing")

    def test_resolve_dependencies_satisfied(self):
        manager = PluginManager()
        m1 = PluginManifest(id="a", name="A", version="1.0.0", entry_point="a:A")
        m2 = PluginManifest(
            id="b", name="B", version="1.0.0",
            entry_point="b:B", dependencies={"a": ">=1.0.0"},
        )
        manager.install(m1)
        manager.install(m2)
        self.assertEqual(len(manager.resolve_dependencies(m2)), 0)

    def test_status(self):
        manager = PluginManager()
        m1 = PluginManifest(id="a", name="A", version="1.0.0", entry_point="a:A")
        m2 = PluginManifest(id="b", name="B", version="1.0.0", entry_point="b:B")
        manager.install(m1)
        manager.install(m2)
        manager.enable("a")
        status = manager.status()
        self.assertEqual(status["total"], 2)
        self.assertEqual(status["enabled"], 1)
        self.assertEqual(status["disabled"], 0)

    def test_satisfies_range(self):
        self.assertTrue(satisfies_range("2.5.0", "2.0.0", "3.0.0"))
        self.assertFalse(satisfies_range("3.5.0", "2.0.0", "3.0.0"))


if __name__ == "__main__":
    unittest.main()