"""Tests for ecosystem monitoring, audit, and security (Stage 22 step 7)."""

from __future__ import annotations

import os
import tempfile
import unittest

from app.ecosystem.monitoring import (
    AuditLog,
    DependencyScanner,
    EcosystemMonitor,
    SecretScrubber,
    SecretVault,
    get_audit_log,
)


class EcosystemMonitorTest(unittest.TestCase):
    def test_record_and_summary(self):
        monitor = EcosystemMonitor()
        monitor.record("plugin.installed", {"plugin_id": "github"}, plugin_id="github")
        monitor.record("plugin.error", error="boom", plugin_id="github")
        summary = monitor.summary()
        self.assertEqual(summary["total_events"], 2)
        self.assertIn("github", summary["plugins"])
        health = monitor.health()
        self.assertIn("status", health)
        # 1 error / 2 events = 50% error rate, which is critical.
        self.assertEqual(health["status"], "critical")

    def test_health_statuses(self):
        monitor = EcosystemMonitor()
        for _ in range(10):
            monitor.record("ok")
        self.assertEqual(monitor.health()["status"], "healthy")
        for _ in range(10):
            monitor.record("fail", error="oops")
        self.assertEqual(monitor.health()["status"], "critical")

    def test_recent(self):
        monitor = EcosystemMonitor()
        for i in range(5):
            monitor.record(f"event_{i}")
        events = monitor.recent(3)
        self.assertEqual(len(events), 3)


class AuditLogTest(unittest.TestCase):
    def test_record_and_tail(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(path=os.path.join(tmp, "audit.jsonl"))
            entry = log.record("system", "plugin.install", "github", status="success")
            self.assertEqual(entry.action, "plugin.install")
            entries = log.tail()
            self.assertEqual(len(entries), 1)

    def test_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AuditLog(path=os.path.join(tmp, "audit.jsonl"))
            log.record("user1", "plugin.install", "a")
            log.record("user2", "plugin.install", "b")
            log.record("user1", "plugin.uninstall", "a")
            self.assertEqual(len(log.filter(actor="user1")), 2)
            self.assertEqual(len(log.filter(action="plugin.install")), 2)


class SecretVaultTest(unittest.TestCase):
    def test_encrypt_decrypt(self):
        vault = SecretVault(key=b"x" * 32)
        ct = vault.encrypt("hello world")
        self.assertEqual(vault.decrypt(ct), "hello world")

    def test_different_keys(self):
        v1 = SecretVault(key=b"a" * 32)
        v2 = SecretVault(key=b"b" * 32)
        ct = v1.encrypt("hello")
        with __import__("contextlib").suppress(Exception):
            self.assertNotEqual(v2.decrypt(ct), "hello")


class DependencyScannerTest(unittest.TestCase):
    def test_find_suspicious(self):
        scanner = DependencyScanner()
        findings = scanner.scan_requirements("pickle\nflask")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["name"], "pickle")

    def test_find_eval(self):
        scanner = DependencyScanner()
        findings = scanner.scan_source("eval('2+2')")
        self.assertGreaterEqual(len(findings), 1)

    def test_find_forbidden(self):
        scanner = DependencyScanner()
        findings = scanner.scan_source("os.system('rm -rf /')")
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "critical")


class SecretScrubberTest(unittest.TestCase):
    def test_scrubs_known_tokens(self):
        payload = {
            "aws": "AKIAABCDEFGHIJKLMNOP",
            "github": "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "safe": "hello world",
        }
        scrubbed = SecretScrubber.scrub(payload)
        self.assertIn("***REDACTED***", scrubbed["aws"])
        self.assertIn("***REDACTED***", scrubbed["github"])
        self.assertEqual(scrubbed["safe"], "hello world")

    def test_scrubs_openai(self):
        scrubbed = SecretScrubber.scrub({"token": "sk-abcdefghijklmnopqrstuvwxyz12345"})
        self.assertIn("***REDACTED***", scrubbed["token"])


if __name__ == "__main__":
    unittest.main()