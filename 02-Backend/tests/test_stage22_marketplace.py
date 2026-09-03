"""Tests for the integration marketplace (Stage 22 step 6)."""

from __future__ import annotations

import os
import tempfile
import unittest

from app.ecosystem.marketplace import (
    Listing,
    ListingCategory,
    ListingRating,
    MarketplaceCatalog,
    get_marketplace_catalog,
    seed_default_catalog,
)
from app.ecosystem.manager import PluginManager
from app.ecosystem.plugins import PluginLifecycleError, PluginManifest


class MarketplaceTest(unittest.TestCase):
    def setUp(self):
        # Force a fresh manager and catalog for isolation.
        self.tmp = tempfile.mkdtemp()
        os.environ["ASTROVOX_PLUGINS_DIR"] = os.path.join(self.tmp, "plugins")
        os.environ["ASTROVOX_PLUGIN_STORAGE"] = os.path.join(self.tmp, "store")
        from app.ecosystem import manager as mgr_mod
        from app.ecosystem import marketplace as mkt_mod
        mgr_mod._GLOBAL_MANAGER = None
        mkt_mod._GLOBAL_CATALOG = None

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        from app.ecosystem import marketplace as mkt_mod
        mkt_mod._GLOBAL_CATALOG = None

    def test_register_and_search(self):
        catalog = MarketplaceCatalog()
        listing = Listing(
            id="l1",
            name="Demo",
            version="1.0.0",
            description="Sample plugin",
            category="developer",
            tags=["git", "ci"],
            author="AstrovoxAI",
            permissions=["network:outgoing"],
        )
        catalog.register(listing)
        results = catalog.search(query="demo")
        self.assertEqual(len(results), 1)
        categories = catalog.categories()
        self.assertEqual(categories[0]["category"], "developer")

    def test_search_by_tag(self):
        catalog = MarketplaceCatalog()
        catalog.register(Listing(id="a", name="A", version="1.0.0", description="x", category="dev", tags=["x"], author="a"))
        catalog.register(Listing(id="b", name="B", version="1.0.0", description="y", category="dev", tags=["y"], author="a"))
        results = catalog.search(tag="x")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "a")

    def test_search_by_category(self):
        catalog = MarketplaceCatalog()
        catalog.register(Listing(id="a", name="A", version="1.0.0", description="x", category="dev", tags=[], author="a"))
        catalog.register(Listing(id="b", name="B", version="1.0.0", description="y", category="prod", tags=[], author="a"))
        results = catalog.search(category="dev")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "a")

    def test_rating_average(self):
        catalog = MarketplaceCatalog()
        catalog.register(Listing(id="l2", name="x", version="1.0.0", description="", category="x", tags=[], author="a"))
        catalog.add_rating("l2", ListingRating(user_id="u1", stars=5))
        catalog.add_rating("l2", ListingRating(user_id="u2", stars=3))
        self.assertAlmostEqual(catalog.listings["l2"].rating_avg, 4.0)
        self.assertEqual(catalog.listings["l2"].rating_count, 2)

    def test_rating_out_of_range(self):
        catalog = MarketplaceCatalog()
        catalog.register(Listing(id="l2", name="x", version="1.0.0", description="", category="x", tags=[], author="a"))
        with self.assertRaises(ValueError):
            catalog.add_rating("l2", ListingRating(user_id="u1", stars=10))

    def test_install(self):
        catalog = MarketplaceCatalog()
        catalog.register(
            Listing(
                id="github",
                name="GitHub",
                version="1.0.0",
                description="GitHub integration",
                category="developer",
                tags=["git"],
                author="AstrovoxAI",
                permissions=["network:outgoing"],
            )
        )
        result = catalog.install("github")
        self.assertEqual(result["listing"]["installed"], True)
        self.assertGreater(result["listing"]["downloads"], 0)

    def test_install_unknown(self):
        catalog = MarketplaceCatalog()
        with self.assertRaises(PluginLifecycleError):
            catalog.install("nonexistent")

    def test_uninstall(self):
        catalog = MarketplaceCatalog()
        catalog.register(
            Listing(
                id="github",
                name="GitHub",
                version="1.0.0",
                description="GitHub integration",
                category="developer",
                tags=[],
                author="AstrovoxAI",
            )
        )
        catalog.install("github")
        result = catalog.uninstall("github")
        self.assertEqual(result["listing"]["installed"], False)

    def test_toggle(self):
        catalog = MarketplaceCatalog()
        catalog.register(
            Listing(
                id="github",
                name="GitHub",
                version="1.0.0",
                description="GitHub integration",
                category="developer",
                tags=[],
                author="AstrovoxAI",
            )
        )
        catalog.install("github")
        # Enable/disable
        catalog.toggle("github", True)
        self.assertTrue(catalog.listings["github"].enabled)
        catalog.toggle("github", False)
        self.assertFalse(catalog.listings["github"].enabled)

    def test_notifications(self):
        catalog = MarketplaceCatalog()
        catalog.register(
            Listing(
                id="x",
                name="X",
                version="2.0.0",
                description="x",
                category="dev",
                tags=[],
                author="a",
            )
        )
        # Install at version 1.0.0
        manifest = PluginManifest(id="x", name="X", version="1.0.0", entry_point="x:X")
        manager = PluginManager()
        manager.install(manifest)
        notifs = catalog.notifications()
        self.assertEqual(len(notifs), 1)
        self.assertEqual(notifs[0]["installed_version"], "1.0.0")
        self.assertEqual(notifs[0]["available_version"], "2.0.0")

    def test_register_from_manifest(self):
        catalog = MarketplaceCatalog()
        manifest = PluginManifest(
            id="x",
            name="X",
            version="1.0.0",
            entry_point="x:X",
            description="desc",
            category="dev",
            tags=["t1"],
            author="me",
            permissions=["network:outgoing"],
        )
        catalog.register_from_manifest(manifest)
        listing = catalog.listings["x"]
        self.assertEqual(listing.description, "desc")
        self.assertEqual(listing.permissions, ["network:outgoing"])
        self.assertIn("network:outgoing", listing.permissions_overview)
        self.assertEqual(len(listing.version_history), 1)


if __name__ == "__main__":
    unittest.main()