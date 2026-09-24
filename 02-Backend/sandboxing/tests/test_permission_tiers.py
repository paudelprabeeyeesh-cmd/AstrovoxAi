import numpy as np
import pytest

from sandboxing.permission_tiers import PermissionEngine, PermissionTier


@pytest.fixture
def engine():
    return PermissionEngine()


def test_read_auto_approved(engine):
    decision = engine.evaluate("SELECT * FROM users", PermissionTier.READ)
    assert decision.approved is True
    assert decision.reversible is True


def test_write_requires_confirmation(engine):
    decision = engine.evaluate("UPDATE users SET x=1", PermissionTier.WRITE)
    assert decision.approved is False
    assert decision.reversible is True


def test_dangerous_denied_by_default(engine):
    decision = engine.evaluate("rm -rf /tmp", PermissionTier.DANGEROUS)
    assert decision.approved is False
    assert decision.reversible is False


def test_dangerous_safe_operation_not_blocked(engine):
    decision = engine.evaluate("echo safe", PermissionTier.DANGEROUS)
    assert decision.approved is True
    assert decision.reversible is True


def test_write_confirmation_approves(engine):
    decision = engine.confirm("UPDATE users SET x=1", PermissionTier.WRITE)
    assert decision.approved is True
    assert decision.message == "write confirmed by user"


def test_reverse_read(engine):
    assert engine.reverse("SELECT 1", PermissionTier.READ) is True


def test_numpy_batch_evaluation(engine):
    operations = np.array(["SELECT 1", "UPDATE t", "rm -rf /", "echo ok"])
    tiers = [PermissionTier.READ, PermissionTier.WRITE, PermissionTier.DANGEROUS, PermissionTier.READ]
    decisions = [engine.evaluate(op, t) for op, t in zip(operations, tiers)]
    approved = np.array([d.approved for d in decisions])
    expected = np.array([True, False, False, True])
    np.testing.assert_array_equal(approved, expected)
