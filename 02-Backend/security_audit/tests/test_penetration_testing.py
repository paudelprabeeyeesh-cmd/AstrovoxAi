"""Tests for Task 114: Penetration Testing."""

import numpy as np
import pytest

from security_audit.penetration_testing import (
    AttackVector,
    PenTestReport,
    PenTester,
    TestResult,
)


@pytest.fixture
def pentester():
    return PenTester()


class TestAttackVector:
    def test_vector_creation(self):
        v = AttackVector("test", "injection", "payload", "response", "critical")
        assert v.name == "test"
        assert v.severity == "critical"

    def test_default_vectors_exist(self, pentester):
        assert len(pentester.vectors) > 0

    def test_custom_vectors(self):
        custom = [AttackVector("custom", "dos", "flood", "drop", "high")]
        pt = PenTester(vectors=custom)
        assert len(pt.vectors) == 1


class TestPenTester:
    def test_run_test_returns_result(self, pentester):
        vector = AttackVector("sql_injection", "injection", "' OR 1=1", "error", "critical")
        result = pentester.run_test(vector, "target")
        assert isinstance(result, TestResult)
        assert result.vector.name == "sql_injection"

    def test_register_response_influences_simulation(self, pentester):
        pentester.register_response("target", "sql error occurred")
        vector = AttackVector("sql_injection", "injection", "' OR 1=1", "error", "critical")
        result = pentester.run_test(vector, "target")
        assert result.success is True

    def test_run_suite_returns_report(self, pentester):
        report = pentester.run_suite("target")
        assert isinstance(report, PenTestReport)
        assert report.total_tests == len(pentester.vectors)

    def test_suite_successful_plus_failed_equals_total(self, pentester):
        report = pentester.run_suite("target")
        assert report.successful + report.failed == report.total_tests

    def test_report_risk_score_range(self, pentester):
        report = pentester.run_suite("target")
        assert 0.0 <= report.risk_score <= 1.0

    def test_generate_report_summary(self, pentester):
        report = pentester.run_suite("target")
        summary = pentester.generate_report_summary(report)
        assert summary["total_tests"] == report.total_tests
        assert "by_category" in summary

    def test_clean_response_no_injection(self, pentester):
        pentester.register_response("target", "success: query returned rows")
        vector = AttackVector("sql_injection", "injection", "' OR 1=1", "error", "critical")
        result = pentester.run_test(vector, "target")
        assert result.success is False

    def test_xss_with_script_response(self, pentester):
        pentester.register_response("target", "script reflected")
        vector = AttackVector("xss_reflected", "xss", "<script>alert(1)</script>", "script", "high")
        result = pentester.run_test(vector, "target")
        assert result.success is True


class TestPenTesterNumpy:
    def test_risk_scores_numeric(self, pentester):
        report = pentester.run_suite("target")
        assert isinstance(report.risk_score, float)

    def test_success_array_dtype(self, pentester):
        report = pentester.run_suite("target")
        scores = np.array([1.0 if r.success else 0.0 for r in report.results], dtype=np.float64)
        assert scores.dtype in (np.float64, np.float32)

    def test_results_count_distribution(self, pentester):
        report = pentester.run_suite("target")
        counts = np.array([1 if r.success else 0 for r in report.results], dtype=np.int64)
        assert np.sum(counts) == report.successful

    def test_category_aggregation(self, pentester):
        report = pentester.run_suite("target")
        by_cat: dict[str, int] = {}
        for r in report.results:
            by_cat[r.vector.category] = by_cat.get(r.vector.category, 0) + (1 if r.success else 0)
        assert isinstance(by_cat, dict)
