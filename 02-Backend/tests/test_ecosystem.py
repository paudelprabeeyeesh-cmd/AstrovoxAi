"""Tests for the Stage 22 platform ecosystem."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone

from app.ecosystem.api_platform import (
    ApiAnalytics,
    ApiErrorCode,
    ApiKeyStore,
    OAuthServer,
    RateLimitPolicy,
    RateLimiter,
    RateLimitScope,
    build_error_response,
    sign_payload,
    verify_signature,
)
from app.ecosystem.integrations import (
    IntegrationClient,
    IntegrationConnection,
    IntegrationProvider,
    IntegrationRegistry,
    IntegrationStore,
    build_pkce_pair,
    sign_state,
    verify_state,
)
from app.ecosystem.marketplace import Listing, ListingRating, MarketplaceCatalog
from app.ecosystem.monitoring import EcosystemMonitor
from app.ecosystem.plugins import (
    HookBus,
    PluginLifecycleError,
    PluginManifest,
    PluginPermission,
    PluginRecord,
    PluginSandbox,
    PluginState,
    get_plugin_manager,
    meets_dependency,
    parse_version,
    satisfies_range,
)
from app.ecosystem.sdk import AstrovoxClient
from app.ecosystem.security import AuditLog, DependencyScanner, SecretScrubber, SecretVault
from app.ecosystem.webhooks import WebhookEvent, WebhookManager, WebhookSubscription


class VersioningTest(unittest.TestCase):
    def test_parse_and_compare(self):
        self.assertTrue(parse_version("1.2.3") < parse_version("1.2.4"))
        self.assertTrue(parse_version("2.0.0") > parse_version("1.9.9"))

    def test_satisfies_range(self):
        self.assertTrue(satisfies_range("2.0.0", "2.0.0", "3.0.0"))
        self.assertFalse(satisfies_range("1.9.9", "2.0.0", "3.0.0"))

    def test_meets_dependency(self):
        self.assertTrue(meets_dependency("1.5.0", ">=1.0.0,<2.0.0"))
        self.assertFalse(meets_dependency("2.0.0", ">=1.0.0,<2.0.0"))


class HookBusTest(unittest.TestCase):
    def test_emit_collects_results(self):
        bus = HookBus()
        results = []
        bus.subscribe("chat", lambda x: results.append(x))
        bus.subscribe("chat", lambda x: results.append(x * 2))
        out = bus.emit("chat", 3)
        self.assertEqual(out, [3, 6])
        self.assertEqual(results, [3, 6])

    def test_emit_isolates_handler_errors(self):
        bus = HookBus()
        bus.subscribe("chat", lambda x: 1 / 0)
        bus.subscribe("chat", lambda x: "ok")
        out = bus.emit("chat", 1)
        self.assertEqual(out, ["ok"])


class SandboxTest(unittest.TestCase):
    def test_grant_and_require(self):
        sandbox = PluginSandbox()
        sandbox.grant(["memory:read"])
        self.assertTrue(sandbox.has("memory:read"))
        sandbox.require("memory:read")
        with self.assertRaises(Exception):
            sandbox.require("network:outgoing")

    def test_register_and_call(self):
        sandbox = PluginSandbox()
        sandbox.register("now", lambda: "today")
        self.assertEqual(sandbox.call("now"), "today")
        with self.assertRaises(Exception):
            sandbox.call("missing")


class PluginLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.environ["ASTROVOX_PLUGINS_DIR"] = os.path.join(self.tmp, "plugins")
        os.environ["ASTROVOX_PLUGIN_STORAGE"] = os.path.join(self.tmp, "store")
        # Force the manager singleton to rebuild.
        from app.ecosystem import plugins as plugin_mod

        plugin_mod._GLOBAL_MANAGER = None

    def test_install_enable_disable_uninstall_bundled(self):
        manager = get_plugin_manager()
        record = manager.install("github")
        self.assertEqual(record.manifest.id, "github")
        self.assertEqual(record.state, PluginState.INSTALLED)
        manager.enable("github")
        record = manager.registry.get("github")
        self.assertEqual(record.state, PluginState.ENABLED)
        manager.disable("github")
        self.assertEqual(manager.registry.get("github").state, PluginState.DISABLED)
        manager.uninstall("github")
        self.assertIsNone(manager.registry.get("github"))

    def test_install_validates_permissions(self):
        manager = get_plugin_manager()
        with self.assertRaises(PluginLifecycleError):
            manager.install("slack", permissions=["made:up"])

    def test_set_config_updates_storage(self):
        manager = get_plugin_manager()
        manager.install("slack")
        manager.set_config("slack", {"default_channel": "#general"})
        self.assertEqual(manager.registry.get("slack").config["default_channel"], "#general")

    def test_invoke_requires_enabled_state(self):
        manager = get_plugin_manager()
        manager.install("slack")
        with self.assertRaises(PluginLifecycleError):
            manager.invoke("slack", "post_message", "#x", "hi")
        manager.enable("slack")
        # No instance will load because no source files exist; invoke should fail.
        with self.assertRaises(PluginLifecycleError):
            manager.invoke("slack", "post_message", "#x", "hi")


class RateLimiterTest(unittest.TestCase):
    def test_default_policies(self):
        limiter = RateLimiter()
        result = limiter.check("authenticated", "key1")
        self.assertTrue(result["allowed"])
        self.assertGreaterEqual(result["remaining"], 0)

    def test_burst_window(self):
        policy = RateLimitPolicy("tiny", RateLimitScope.PER_KEY, limit=2, window_seconds=60)
        limiter = RateLimiter([policy])
        self.assertTrue(limiter.check("tiny", "k")["allowed"])
        self.assertTrue(limiter.check("tiny", "k")["allowed"])
        self.assertFalse(limiter.check("tiny", "k")["allowed"])


class ApiKeyStoreTest(unittest.TestCase):
    def test_issue_and_verify(self):
        store = ApiKeyStore()
        record, key, secret = store.issue("owner", "lbl", ["read", "write"])
        self.assertTrue(store.verify(key, secret))
        self.assertFalse(store.verify(key, "wrong"))
        self.assertEqual(record.last_used, None)

    def test_revoke(self):
        store = ApiKeyStore()
        record, key, secret = store.issue("o", "l", ["read"])
        store.revoke(record.id)
        self.assertIsNone(store.verify(key, secret))


class OAuthServerTest(unittest.TestCase):
    def test_full_flow(self):
        server = OAuthServer()
        client, secret = server.register_client("demo", ["https://x"], ["read"])
        code = server.authorization_code(client.id, "user-1", "https://x", "read", state="abc")
        token = server.exchange_code(code, client.id, "https://x")
        self.assertIsNotNone(token)
        self.assertEqual(token.scope, "read")
        introspected = server.introspect(token.access_token)
        self.assertTrue(introspected["active"])

    def test_client_credentials(self):
        server = OAuthServer()
        client, secret = server.register_client("demo", [])
        token = server.client_credentials(client.id, "read")
        self.assertIsNotNone(token)


class SignatureTest(unittest.TestCase):
    def test_roundtrip(self):
        payload = b"hello"
        secret = "topsecret"
        signature = sign_payload(payload, secret)
        self.assertTrue(verify_signature(payload, signature, secret))

    def test_replay_protection(self):
        payload = b"hello"
        secret = "topsecret"
        signature = sign_payload(payload, secret, timestamp=1)
        self.assertFalse(verify_signature(payload, signature, secret))


class AnalyticsTest(unittest.TestCase):
    def test_record_and_summary(self):
        analytics = ApiAnalytics()
        from app.ecosystem.api_platform import ApiCall

        for i in range(5):
            analytics.record(
                ApiCall(
                    timestamp=i,
                    endpoint="/v1/chat/completions",
                    method="POST",
                    status=200 if i % 2 else 500,
                    latency_ms=10 + i,
                    key_id="k",
                )
            )
        summary = analytics.summary()
        self.assertEqual(summary["total_calls"], 5)
        self.assertGreater(summary["error_rate"], 0)
        perf = analytics.endpoint_perf("POST /v1/chat/completions")
        self.assertEqual(perf["count"], 5)


class IntegrationRegistryTest(unittest.TestCase):
    def test_catalog_lists_all_providers(self):
        registry = IntegrationRegistry()
        items = registry.list()
        ids = {i["provider"] for i in items}
        self.assertIn("github", ids)
        self.assertIn("slack", ids)
        self.assertIn("notion", ids)
        self.assertTrue(registry.by_category("storage"))


class IntegrationClientTest(unittest.TestCase):
    def setUp(self):
        self.store = IntegrationStore()
        self.conn = IntegrationConnection(
            id="int-1",
            provider=IntegrationProvider.GITHUB,
            owner_id="u1",
            label="test",
            status="connected",
            access_token="x",
        )
        self.store.add(self.conn)
        self.client = IntegrationClient(self.store)

    def test_github_actions(self):
        out = self.client.github_list_repos(self.conn.id, owner="astrovox-ai")
        self.assertTrue(out["ok"])
        issue = self.client.github_create_issue(self.conn.id, "astrovox-ai/repo", "Bug", "details")
        self.assertTrue(issue["ok"])

    def test_storage_actions(self):
        store_conn = IntegrationConnection(
            id="int-2",
            provider=IntegrationProvider.GOOGLE_DRIVE,
            owner_id="u1",
            label="drive",
        )
        self.store.add(store_conn)
        out = self.client.storage_list_files(store_conn.id, "root")
        self.assertTrue(out["ok"])
        upload = self.client.storage_upload(store_conn.id, "x.txt", b"hello", folder_id="root")
        self.assertTrue(upload["ok"])

    def test_missing_connection_raises(self):
        with self.assertRaises(ValueError):
            self.client.github_list_repos("missing")


class PkceTest(unittest.TestCase):
    def test_pair_unique(self):
        v1, c1 = build_pkce_pair()
        v2, c2 = build_pkce_pair()
        self.assertNotEqual(v1, v2)
        self.assertNotEqual(c1, c2)
        self.assertGreater(len(v1), 40)


class StateSigningTest(unittest.TestCase):
    def test_roundtrip(self):
        secret = "s"
        payload = {"a": 1}
        token = sign_state(payload, secret)
        self.assertEqual(verify_state(token, secret), payload)
        self.assertIsNone(verify_state(token + "tamper", secret))


class WebhookManagerTest(unittest.TestCase):
    def test_signing_roundtrip(self):
        manager = WebhookManager(http_post=lambda url, body, headers: 200)
        body = b'{"event":"chat.completed"}'
        sig = sign_payload(body, "secret")
        self.assertTrue(manager.verify_incoming(body, sig, "secret"))

    def test_publish_and_metrics(self):
        async def fake_post(url, body, headers):
            return 200

        manager = WebhookManager(http_post=fake_post)
        manager.create_subscription(
            url="https://example.com/wh",
            events=["*"],
            owner_id="u1",
            secret="abc",
        )
        import asyncio

        deliveries = asyncio.run(manager.publish("chat.completed", {"x": 1}, target_owner="u1"))
        self.assertEqual(len(deliveries), 1)
        metrics = manager.metrics()
        self.assertEqual(metrics["events"].get("delivered"), 1)


class MarketplaceTest(unittest.TestCase):
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

    def test_rating_average(self):
        catalog = MarketplaceCatalog()
        catalog.register(
            Listing(
                id="l2",
                name="x",
                version="1.0.0",
                description="",
                category="x",
                tags=[],
                author="a",
            )
        )
        catalog.add_rating("l2", ListingRating(user_id="u1", stars=5))
        catalog.add_rating("l2", ListingRating(user_id="u2", stars=3))
        self.assertAlmostEqual(catalog.listings["l2"].rating_avg, 4.0)


class EcosystemMonitorTest(unittest.TestCase):
    def test_record_and_summary(self):
        monitor = EcosystemMonitor()
        monitor.record("plugin.installed", {"plugin_id": "github"}, plugin_id="github")
        monitor.record("plugin.installed", {}, plugin_id="github", payload={"error": "boom"})
        summary = monitor.summary()
        self.assertEqual(summary["total_events"], 2)
        self.assertIn("github", summary["plugins"])
        health = monitor.health()
        self.assertIn("status", health)


class AuditLogTest(unittest.TestCase):
    def test_record_and_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(path=os.path.join(tmp, "audit.jsonl"))
            entry = log.record("system", "plugin.install", "github", status="success")
            self.assertEqual(entry.action, "plugin.install")
            entries = log.tail()
            self.assertEqual(len(entries), 1)


class SecretVaultTest(unittest.TestCase):
    def test_encrypt_decrypt(self):
        vault = SecretVault(key=b"x" * 32)
        ct = vault.encrypt("hello world")
        self.assertEqual(vault.decrypt(ct), "hello world")


class DependencyScannerTest(unittest.TestCase):
    def test_find_eval(self):
        scanner = DependencyScanner()
        findings = scanner.scan_source("eval('2+2')")
        self.assertGreaterEqual(len(findings), 1)


class SecretScrubberTest(unittest.TestCase):
    def test_scrubs_known_tokens(self):
        payload = {"token": "AKIAABCDEFGHIJKLMNOP"}
        scrubbed = SecretScrubber.scrub(payload)
        self.assertIn("***REDACTED***", scrubbed["token"])


class ErrorEnvelopeTest(unittest.TestCase):
    def test_error_envelope(self):
        exc = build_error_response(ApiErrorCode.FORBIDDEN, "denied", 403, scope="admin")
        self.assertEqual(exc.status_code, 403)
        self.assertEqual(exc.detail["error"]["code"], "forbidden")


if __name__ == "__main__":
    unittest.main()