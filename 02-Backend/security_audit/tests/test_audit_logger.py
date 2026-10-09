"""Tests for audit_logger module."""

import pytest

from security_audit.audit_logger import AuditFilter, AuditLogger, AuditStats, LogEntry


@pytest.fixture
def logger():
    return AuditLogger()


class TestLogEntry:
    def test_entry_creation(self):
        entry = LogEntry(timestamp=1000.0, actor="admin", action="login", resource="/api", outcome="success")
        assert entry.actor == "admin"
        assert entry.outcome == "success"

    def test_entry_checksum_generated(self, logger):
        entry = logger.log("admin", "login", "/api", "success")
        assert len(entry.checksum) == 16

    def test_entry_metadata_default(self, logger):
        entry = logger.log("user", "read", "/data", "denied")
        assert isinstance(entry.metadata, dict)


class TestAuditFilter:
    def test_filter_by_actor(self, logger):
        logger.log("alice", "login", "/api", "ok")
        logger.log("bob", "login", "/api", "ok")
        f = AuditFilter(actor="alice")
        results = logger.filter(f)
        assert len(results) == 1
        assert results[0].actor == "alice"

    def test_filter_by_action(self, logger):
        logger.log("a", "login", "/api", "ok")
        logger.log("a", "logout", "/api", "ok")
        f = AuditFilter(action="login")
        results = logger.filter(f)
        assert len(results) == 1

    def test_filter_by_time_range(self, logger):
        e1 = logger.log("a", "x", "y", "z")
        f = AuditFilter(start_time=e1.timestamp + 1.0)
        results = logger.filter(f)
        assert len(results) == 0

    def test_filter_empty_returns_all(self, logger):
        logger.log("a", "x", "y", "z")
        logger.log("b", "p", "q", "r")
        results = logger.filter(AuditFilter())
        assert len(results) == 2


class TestAuditLogger:
    def test_log_returns_entry(self, logger):
        entry = logger.log("admin", "config_change", "/system", "success")
        assert isinstance(entry, LogEntry)

    def test_log_stores_entry(self, logger):
        logger.log("admin", "config_change", "/system", "success")
        assert len(logger._entries) == 1

    def test_multiple_logs(self, logger):
        for i in range(5):
            logger.log(f"user{i}", "action", "res", "ok")
        assert len(logger._entries) == 5

    def test_verify_chain_empty(self, logger):
        assert logger.verify_chain() is True

    def test_verify_chain_single(self, logger):
        logger.log("a", "x", "y", "z")
        assert logger.verify_chain() is True

    def test_verify_chain_multiple(self, logger):
        logger.log("a", "x", "y", "z")
        logger.log("b", "p", "q", "r")
        assert logger.verify_chain() is True

    def test_compute_stats_empty(self, logger):
        stats = logger.compute_stats()
        assert stats.total_entries == 0
        assert stats.actor_counts == {}

    def test_compute_stats_counts(self, logger):
        logger.log("alice", "login", "/api", "ok")
        logger.log("alice", "read", "/data", "ok")
        logger.log("bob", "login", "/api", "ok")
        stats = logger.compute_stats()
        assert stats.total_entries == 3
        assert stats.actor_counts["alice"] == 2
        assert stats.actor_counts["bob"] == 1

    def test_export_json(self, logger):
        logger.log("admin", "login", "/api", "success")
        exported = logger.export_json()
        assert "admin" in exported
        assert "login" in exported

    def test_export_json_is_valid_json(self, logger):
        import json
        logger.log("a", "x", "y", "z")
        exported = logger.export_json()
        parsed = json.loads(exported)
        assert isinstance(parsed, list)

    def test_metadata_in_export(self, logger):
        logger.log("user", "action", "res", "outcome", metadata={"ip": "1.2.3.4"})
        exported = logger.export_json()
        assert "ip" in exported

    def test_checksum_consistency(self, logger):
        e1 = logger.log("a", "x", "y", "z")
        e2 = logger.log("a", "x", "y", "z")
        assert e1.checksum == e2.checksum
