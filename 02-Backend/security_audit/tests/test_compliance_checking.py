"""Tests for Task 114: Compliance Checking."""

import numpy as np
import pytest

from security_audit.compliance_checking import (
    AuditEntry,
    ComplianceChecker,
    ComplianceResult,
    PolicyRule,
)


@pytest.fixture
def checker():
    return ComplianceChecker()


class TestPolicyRule:
    def test_policy_creation(self):
        rule = PolicyRule("P1", "Test", "Desc", "check_key", "high", "cat")
        assert rule.rule_id == "P1"
        assert rule.severity == "high"

    def test_default_policies_exist(self, checker):
        assert len(checker.policies) > 0


class TestAuditEntry:
    def test_entry_hash_generated(self, checker):
        entry = checker.record_action("admin", "login", "/api", "success")
        assert len(entry.entry_hash) == 16

    def test_entry_timestamp_set(self, checker):
        import time
        ts = time.time()
        entry = checker.record_action("user", "access", "/data", "denied")
        assert abs(entry.timestamp - ts) < 1.0

    def test_verify_chain_single_entry(self, checker):
        checker.record_action("a", "x", "y", "z")
        assert checker.verify_chain() is True

    def test_verify_chain_multiple(self, checker):
        checker.record_action("a", "x", "y", "z")
        checker.record_action("b", "p", "q", "r")
        assert checker.verify_chain() is True


class TestComplianceChecker:
    def test_evaluate_policy_passed(self, checker):
        rule = PolicyRule("P1", "R", "D", "key", "high", "cat")
        result = checker.evaluate_policy(rule, {"key": True})
        assert result.passed is True
        assert result.violations == 0

    def test_evaluate_policy_failed(self, checker):
        rule = PolicyRule("P1", "R", "D", "key", "high", "cat")
        result = checker.evaluate_policy(rule, {"key": False})
        assert result.passed is False
        assert result.violations == 1

    def test_full_assessment_all_pass(self, checker):
        checks = {p.check: True for p in checker.policies}
        results, score = checker.full_assessment(checks)
        assert score == 1.0
        assert all(r.passed for r in results)

    def test_full_assessment_all_fail(self, checker):
        checks = {p.check: False for p in checker.policies}
        results, score = checker.full_assessment(checks)
        assert score == 0.0
        assert all(not r.passed for r in results)

    def test_assessment_score_range(self, checker):
        checks = {p.check: True for p in checker.policies}
        _, score = checker.full_assessment(checks)
        assert 0.0 <= score <= 1.0

    def test_get_audit_trail_filter_by_actor(self, checker):
        checker.record_action("alice", "login", "/api", "ok")
        checker.record_action("bob", "login", "/api", "ok")
        trail = checker.get_audit_trail(actor="alice")
        assert len(trail) == 1
        assert trail[0].actor == "alice"

    def test_record_action_stores_entry(self, checker):
        entry = checker.record_action("admin", "config_change", "/system", "success")
        assert entry in checker._audit_trail


class TestComplianceCheckerNumpy:
    def test_score_numeric(self, checker):
        checks = {p.check: True for p in checker.policies}
        _, score = checker.full_assessment(checks)
        assert isinstance(score, float)

    def test_results_array(self, checker):
        checks = {p.check: True for p in checker.policies}
        results, score = checker.full_assessment(checks)
        scores = np.array([1.0 if r.passed else 0.0 for r in results], dtype=np.float64)
        assert scores.dtype in (np.float64, np.float32)

    def test_violation_counts(self, checker):
        checks = {p.check: False for p in checker.policies}
        results, score = checker.full_assessment(checks)
        violations = np.array([r.violations for r in results], dtype=np.int64)
        assert np.sum(violations) == len(results)

    def test_audit_entry_count(self, checker):
        for i in range(20):
            checker.record_action(f"user{i}", "action", "res", "ok")
        assert len(checker._audit_trail) == 20
