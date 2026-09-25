"""Tests for database_helpers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database_helpers import (
    AuditColumnsMixin,
    BackupManifest,
    BackupManifestGenerator,
    BatchUpsert,
    ColumnDiff,
    DriftReport,
    EncryptionEngine,
    EncryptionError,
    FullTextSearch,
    JsonQuery,
    JsonPathResult,
    PoolHealth,
    PoolHealthCheck,
    QueryTimeoutManager,
    ReplicaRouter,
    RestoreSmokeTest,
    SchemaDriftDetector,
    SeedLoader,
    SeedResult,
    SmokeResult,
    SoftDeleteMixin,
    TransactionRetry,
)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()


@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


class TestSoftDeleteMixin:
    def test_soft_delete_sets_flags(self, sqlite_engine):
        with sqlite_engine.connect() as conn:
            user = User(id=1, name="test")
            user.soft_delete()
            assert user.is_deleted is True
            assert user.deleted_at is not None

    def test_restore_clears_flags(self, sqlite_engine):
        with sqlite_engine.connect() as conn:
            user = User(id=1, name="test")
            user.soft_delete()
            user.restore()
            assert user.is_deleted is False
            assert user.deleted_at is None


class TestAuditColumnsMixin:
    def test_defaults_are_datetimes(self):
        class Audited(Base, AuditColumnsMixin):
            __tablename__ = "audited"
            id: Mapped[int] = mapped_column(primary_key=True)

        assert Audited.created_at is not None


class TestEncryptionEngine:
    def test_roundtrip(self):
        engine = EncryptionEngine(secret_key="test-secret-key-1234567890123456789012")
        encrypted = engine.encrypt("hello")
        assert encrypted != "hello"
        assert engine.decrypt(encrypted) == "hello"

    def test_empty_input(self):
        engine = EncryptionEngine(secret_key="test-secret-key-1234567890123456789012")
        assert engine.encrypt("") == ""
        assert engine.decrypt("") == ""

    def test_decrypt_invalid_raises(self):
        engine = EncryptionEngine(secret_key="test-secret-key-1234567890123456789012")
        with pytest.raises(EncryptionError):
            engine.decrypt("not-valid-base64!!!")

    def test_encrypt_dict(self):
        engine = EncryptionEngine(secret_key="test-secret-key-1234567890123456789012")
        result = engine.encrypt_dict({"name": "alice", "ssn": "123-45-6789"}, ["ssn"])
        assert result["name"] == "alice"
        assert result["ssn"] != "123-45-6789"

    def test_decrypt_dict(self):
        engine = EncryptionEngine(secret_key="test-secret-key-1234567890123456789012")
        enc = engine.encrypt_dict({"name": "alice", "ssn": "123-45-6789"}, ["ssn"])
        result = engine.decrypt_dict(enc, ["ssn"])
        assert result["ssn"] == "123-45-6789"


class TestTransactionRetry:
    def test_succeeds_first_try(self):
        retry = TransactionRetry(max_retries=3)
        result = retry.run(lambda: 42)
        assert result == 42

    def test_retries_then_succeeds(self):
        calls = [0]

        def flaky():
            calls[0] += 1
            if calls[0] < 3:
                raise OperationalError("boom", None, None)
            return "ok"

        retry = TransactionRetry(max_retries=5, base_delay=0.01, max_delay=0.05)
        result = retry.run(flaky)
        assert result == "ok"
        assert calls[0] == 3

    def test_raises_after_exhausting(self):
        retry = TransactionRetry(max_retries=2, base_delay=0.01)
        with pytest.raises(OperationalError):
            retry.run(lambda: (_ for _ in ()).throw(OperationalError("dead", None, None)))


class TestQueryTimeoutManager:
    def test_execute_with_timeout(self, sqlite_engine):
        mgr = QueryTimeoutManager(sqlite_engine, default_timeout_ms=1000)
        with mgr.timeout(5000):
            with sqlite_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        assert True


class TestPoolHealthCheck:
    def test_returns_health(self, sqlite_engine):
        check = PoolHealthCheck(sqlite_engine)
        health = check.check()
        assert health.status in {"healthy", "degraded", "saturated", "unhealthy"}
        assert health.checked_at != ""

    def test_summary(self, sqlite_engine):
        check = PoolHealthCheck(sqlite_engine)
        summary = check.summary()
        assert "status" in summary
        assert "latency_ms" in summary


class TestSeedLoader:
    def test_load_dict_inserts_rows(self, sqlite_engine):
        loader = SeedLoader(sqlite_engine)
        with sqlite_engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.commit()
        results = loader.load_dict({"items": [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]}, truncate=True)
        assert len(results) == 1
        assert results[0].inserted == 2
        assert results[0].skipped == 0


class TestBackupManifest:
    def test_roundtrip(self, tmp_path):
        manifest = BackupManifest(tables=["users"], row_counts={"users": 10}, files=["users.sql"], size_bytes=1024)
        path = tmp_path / "manifest.json"
        manifest.to_json(path)
        loaded = BackupManifest.from_json(path)
        assert loaded.tables == ["users"]
        assert loaded.row_counts["users"] == 10


class TestRestoreSmokeTest:
    def test_passes_with_data(self, sqlite_engine):
        with sqlite_engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY)"))
            conn.execute(text("INSERT INTO items (id) VALUES (1)"))
            conn.commit()
        test = RestoreSmokeTest("sqlite:///:memory:")
        with test._engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY)"))
            conn.execute(text("INSERT INTO items (id) VALUES (1)"))
            conn.commit()
        result = test.run(["items"], min_rows={"items": 1})
        assert result.passed is True
        assert any(c["name"] == "tables_exist" and c["passed"] for c in result.checks)


class TestSchemaDriftDetector:
    def test_clean_schema(self, sqlite_engine):
        detector = SchemaDriftDetector(sqlite_engine, Base)
        report = detector.detect()
        assert report.is_clean is True

    def test_detects_missing_table(self, sqlite_engine):
        class Missing(Base):
            __tablename__ = "missing"
            id: Mapped[int] = mapped_column(primary_key=True)
        detector = SchemaDriftDetector(sqlite_engine, Missing)
        report = detector.detect()
        assert "missing" in report.missing_tables


class TestJsonQuery:
    def test_get_and_contains(self, sqlite_engine):
        with sqlite_engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, data JSONB)"))
            conn.execute(text("INSERT INTO items (id, data) VALUES (1, '{\"a\": {\"b\": \"c\"}}')"))
            conn.commit()
        jq = JsonQuery(sqlite_engine)
        assert jq.get("items", "data", 1, "a.b") == "c"
        assert jq.exists("items", "data", 1, "a.b") is True
        assert jq.exists("items", "data", 1, "a.x") is False
