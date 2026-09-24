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
