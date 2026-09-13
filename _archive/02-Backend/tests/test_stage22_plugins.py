"""Tests for the plugin framework foundation (Stage 22 step 1)."""

from __future__ import annotations

import unittest

from app.ecosystem.plugins import (
    PluginLifecycleError,
    PluginLoader,
    PluginManifest,
    PluginPermission,
    PluginRecord,
    PluginRegistry,
    PluginState,
    meets_dependency,
    parse_version,
    satisfies_range,
)


class VersioningTest(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3, ""))

    def test_satisfies_range(self):
        self.assertTrue(satisfies_range("2.0.0", "2.0.0", "3.0.0"))
        self.assertFalse(satisfies_range("1.9.9", "2.0.0", "3.0.0"))

    def test_meets_dependency(self):
        self.assertTrue(meets_dependency("1.5.0", ">=1.0.0,<2.0.0"))
        self.assertFalse(meets_dependency("2.0.0", ">=1.0.0,<2.0.0"))


class PluginLoaderTest(unittest.TestCase):
    def test_validate_missing_fields(self):
        errors = PluginLoader.validate_manifest({})
        self.assertGreater(len(errors), 0)

    def test_validate_unknown_permission(self):
        errors = PluginLoader.validate_manifest(
            {"id": "x", "name": "x", "version": "1.0.0", "entry_point": "x:y", "permissions": ["made:up"]}
        )
        self.assertTrue(any("Unknown permissions" in e for e in errors))

    def test_validate_bad_id(self):
        errors = PluginLoader.validate_manifest(
            {"id": "BadID", "name": "x", "version": "1.0.0", "entry_point": "x:y"}
        )
        self.assertTrue(any("lowercase" in e for e in errors))

    def test_load_manifest_from_dict(self):
        manifest = PluginLoader.load_manifest_from_dict(
            {
                "id": "github",
                "name": "GitHub",
                "version": "1.0.0",
                "entry_point": "github:Plugin",
                "permissions": ["network:outgoing"],
            }
        )
        self.assertEqual(manifest.id, "github")
        self.assertIn("network:outgoing", manifest.permissions)

    def test_load_manifest_invalid_raises(self):
        with self.assertRaises(PluginLifecycleError):
            PluginLoader.load_manifest_from_dict({})

    def test_checksum(self):
        self.assertEqual(len(PluginLoader.checksum_bytes(b"hello")), 64)


class PluginRegistryTest(unittest.TestCase):
    def test_add_get_remove(self):
        registry = PluginRegistry()
        manifest = PluginManifest(id="p1", name="P1", version="1.0.0", entry_point="p1:Plugin")
        record = PluginRecord(manifest=manifest)
        registry.add(record)
        self.assertIs(registry.get("p1"), record)
        self.assertIn("p1", registry.ids())
        self.assertIs(registry.remove("p1"), record)
        self.assertIsNone(registry.get("p1"))

    def test_by_state(self):
        registry = PluginRegistry()
        m1 = PluginManifest(id="a", name="A", version="1.0.0", entry_point="a:Plugin")
        m2 = PluginManifest(id="b", name="B", version="1.0.0", entry_point="b:Plugin")
        registry.add(PluginRecord(manifest=m1, state=PluginState.ENABLED))
        registry.add(PluginRecord(manifest=m2, state=PluginState.DISABLED))
        enabled = registry.by_state(PluginState.ENABLED)
        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].manifest.id, "a")

    def test_by_category(self):
        registry = PluginRegistry()
        m = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:Plugin", category="dev")
        registry.add(PluginRecord(manifest=m))
        self.assertEqual(len(registry.by_category("dev")), 1)


if __name__ == "__main__":
    unittest.main()