import pytest
from resource_management import Quota, QuotaManager


def test_consume_allows_under_limit():
    qm = QuotaManager()
    qm.set_limit("user", Quota(requests=2))
    assert qm.consume("user", Quota(requests=1)) is True
    assert qm.consume("user", Quota(requests=1)) is True


def test_consume_blocks_over_limit():
    qm = QuotaManager()
    qm.set_limit("user", Quota(requests=2))
    assert qm.consume("user", Quota(requests=1)) is True
    assert qm.consume("user", Quota(requests=2)) is False


def test_report_reflects_usage():
    qm = QuotaManager()
    qm.consume("user", Quota(cpu_seconds=1.0, requests=1))
    report = qm.report()
    assert report["user"]["cpu_seconds"] == 1.0
    assert report["user"]["requests"] == 1


def test_reset_clears_usage():
    qm = QuotaManager()
    qm.consume("user", Quota(requests=1))
    qm.reset("user")
    assert qm.report() == {}


def test_consume_without_limit():
    qm = QuotaManager()
    assert qm.consume("user", Quota(requests=10)) is True
    assert qm.consume("user", Quota(requests=10)) is True


def test_multiple_subjects():
    qm = QuotaManager()
    qm.set_limit("alice", Quota(requests=2))
    qm.set_limit("bob", Quota(requests=3))
    assert qm.consume("alice", Quota(requests=2)) is True
    assert qm.consume("bob", Quota(requests=3)) is True
    assert qm.consume("alice", Quota(requests=1)) is False
    assert qm.consume("bob", Quota(requests=1)) is False


def test_limit_cpu_seconds_and_memory():
    qm = QuotaManager()
    qm.set_limit("user", Quota(cpu_seconds=5.0, memory_bytes=100))
    assert qm.consume("user", Quota(cpu_seconds=3.0, memory_bytes=50)) is True
    assert qm.consume("user", Quota(cpu_seconds=3.0, memory_bytes=50)) is False
    assert qm.consume("user", Quota(cpu_seconds=1.0, memory_bytes=60)) is False


def test_io_bytes_recorded_without_limit():
    qm = QuotaManager()
    qm.consume("user", Quota(io_bytes=10))
    report = qm.report()
    assert report["user"]["io_bytes"] == 10


def test_set_limit_updates_existing():
    qm = QuotaManager()
    qm.set_limit("user", Quota(requests=1))
    qm.consume("user", Quota(requests=1))
    qm.set_limit("user", Quota(requests=5))
    assert qm.consume("user", Quota(requests=4)) is True


def test_report_multiple_subjects():
    qm = QuotaManager()
    qm.set_limit("a", Quota(requests=1))
    qm.set_limit("b", Quota(requests=2))
    qm.consume("a", Quota(requests=1))
    qm.consume("b", Quota(requests=2))
    report = qm.report()
    assert report["a"]["requests"] == 1
    assert report["b"]["requests"] == 2
