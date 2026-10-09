"""Tests for compliance_checker module."""

import pytest

from security_audit.compliance_checker import ComplianceChecker, ComplianceReport, ComplianceResult, ComplianceRule


@pytest.fixture
def checker():
    return ComplianceChecker()


@pytest.fixture
def sample_rules():
    return [
        ComplianceRule("C-001", "Password Policy", "Passwords rotated every 90 days", "password_rotation", "high", "enabled"),
        ComplianceRule("C-002", "MFA Required", "MFA enabled for admins", "mfa_enabled", "critical", "true"),
        ComplianceRule("C-003", "TLS Version", "TLS 1.2+ required", "tls_version", "high", "TLSv1.2"),
    ]


class TestComplianceRule:
    def test_rule_creation(self):
        rule = ComplianceRule("R1", "Test", "Desc", "check_key", "high", "expected_val")
        assert rule.rule_id == "R1"
        assert rule.severity == "high"

    def test_rule_defaults(self):
        rule = ComplianceRule("R2", "T", "D", "k", "low", "val")
        assert rule.check_type == "k"


class TestComplianceChecker:
    def test_add_rule(self, checker):
        rule = ComplianceRule("R1", "Test", "Desc", "check", "high", "enabled")
        checker.add_rule(rule)
        assert len(checker.rules) == 1

    def test_evaluate_passed(self, checker):
        rule = ComplianceRule("R1", "Test", "Desc", "key", "high", "enabled")
        result = checker.evaluate(rule, "enabled")
        assert result.passed is True
        assert result.actual == "enabled"

    def test_evaluate_failed(self, checker):
        rule = ComplianceRule("R1", "Test", "Desc", "key", "high", "enabled")
        result = checker.evaluate(rule, "disabled")
        assert result.passed is False
        assert "Failed" in result.details

    def test_evaluate_case_insensitive(self, checker):
        rule = ComplianceRule("R1", "Test", "Desc", "key", "high", "enabled")
        result = checker.evaluate(rule, "ENABLED")
        assert result.passed is True

    def test_full_assessment_all_pass(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "true", "tls_version": "TLSv1.2"}
        report = checker.full_assessment(checks)
        assert report.passed_count == 3
        assert report.failed_count == 0
        assert report.score == 1.0

    def test_full_assessment_all_fail(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "disabled", "mfa_enabled": "false", "tls_version": "TLSv1.0"}
        report = checker.full_assessment(checks)
        assert report.passed_count == 0
        assert report.failed_count == 3
        assert report.score == 0.0

    def test_full_assessment_score_range(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "false", "tls_version": "TLSv1.2"}
        report = checker.full_assessment(checks)
        assert 0.0 <= report.score <= 1.0

    def test_full_assessment_empty_rules(self, checker):
        report = checker.full_assessment({})
        assert report.rules_checked == 0
        assert report.score == 0.0

    def test_get_failed(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "false", "tls_version": "TLSv1.0"}
        report = checker.full_assessment(checks)
        failed = checker.get_failed(report)
        assert len(failed) == 2

    def test_get_failed_empty_when_all_pass(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "true", "tls_version": "TLSv1.2"}
        report = checker.full_assessment(checks)
        failed = checker.get_failed(report)
        assert len(failed) == 0

    def test_compute_score_bounds(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "false", "tls_version": "TLSv1.0"}
        report = checker.full_assessment(checks)
        score = checker.compute_score(report)
        assert 0.0 <= score <= 1.0

    def test_report_structure(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "true", "tls_version": "TLSv1.2"}
        report = checker.full_assessment(checks)
        assert isinstance(report, ComplianceReport)
        assert report.rules_checked == 3
        assert isinstance(report.results, list)

    def test_evaluate_missing_actual(self, checker):
        rule = ComplianceRule("R1", "Test", "Desc", "missing", "high", "enabled")
        result = checker.evaluate(rule, "unknown")
        assert result.passed is False
        assert "unknown" in result.details


class TestComplianceReport:
    def test_report_initialization(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "enabled", "mfa_enabled": "true", "tls_version": "TLSv1.2"}
        report = checker.full_assessment(checks)
        assert report.passed_count == 3
        assert report.failed_count == 0

    def test_report_has_results_list(self, checker, sample_rules):
        checker.rules = sample_rules
        checks = {"password_rotation": "disabled", "mfa_enabled": "false", "tls_version": "TLSv1.0"}
        report = checker.full_assessment(checks)
        assert len(report.results) == 3
        assert all(isinstance(r, ComplianceResult) for r in report.results)
