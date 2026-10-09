"""Tests for Task 114: Security Hardening."""

import numpy as np
import pytest

from security_audit.security_hardening import (
    HardeningRule,
    SecurityHardener,
)


@pytest.fixture
def hardener():
    return SecurityHardener()


class TestHardeningRule:
    def test_rule_creation(self):
        rule = HardeningRule("H-001", "Test Rule", "Desc", "config_key", "expected_val", "high", "network")
        assert rule.rule_id == "H-001"
        assert rule.severity == "high"

    def test_default_rules_exist(self, hardener):
        assert len(hardener.rules) > 0


class TestSecurityHardener:
    def test_evaluate_config_all_pass(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        assert all(r.passed for r in results)

    def test_evaluate_config_all_fail(self, hardener):
        config = {r.check: "wrong_value" for r in hardener.rules}
        results = hardener.evaluate_config(config)
        assert all(not r.passed for r in results)

    def test_compliance_score_perfect(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        score = hardener.compliance_score(results)
        assert score == 1.0

    def test_compliance_score_zero(self, hardener):
        config = {r.check: "wrong" for r in hardener.rules}
        results = hardener.evaluate_config(config)
        score = hardener.compliance_score(results)
        assert score == 0.0

    def test_compliance_score_partial(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        config[hardener.rules[0].check] = "wrong"
        results = hardener.evaluate_config(config)
        score = hardener.compliance_score(results)
        assert 0.0 < score < 1.0

    def test_remediation_plan(self, hardener):
        config = {r.check: "wrong" for r in hardener.rules}
        results = hardener.evaluate_config(config)
        plan = hardener.remediation_plan(results)
        assert len(plan) == len(results)

    def test_remediation_plan_empty_when_all_pass(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        plan = hardener.remediation_plan(results)
        assert len(plan) == 0

    def test_category_scores(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        scores = hardener.category_scores(results)
        assert all(0.0 <= s <= 1.0 for s in scores.values())

    def test_custom_rules(self):
        custom = [HardeningRule("H-X", "Custom", "Desc", "x", "y", "low", "custom")]
        h = SecurityHardener(rules=custom)
        assert len(h.rules) == 1


class TestSecurityHardenerNumpy:
    def test_score_numeric(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        score = hardener.compliance_score(results)
        assert isinstance(score, float)

    def test_results_array_dtype(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        scores = np.array([1.0 if r.passed else 0.0 for r in results], dtype=np.float64)
        assert scores.dtype in (np.float64, np.float32)

    def test_partial_scores_array(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        config[hardener.rules[1].check] = "wrong"
        results = hardener.evaluate_config(config)
        scores = np.array([1.0 if r.passed else 0.0 for r in results], dtype=np.float64)
        assert np.mean(scores) < 1.0

    def test_category_score_means(self, hardener):
        config = {r.check: r.expected for r in hardener.rules}
        results = hardener.evaluate_config(config)
        cat_scores = hardener.category_scores(results)
        assert all(0.0 <= v <= 1.0 for v in cat_scores.values())
