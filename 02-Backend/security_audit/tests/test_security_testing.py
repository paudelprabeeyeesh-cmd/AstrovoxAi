"""Tests for Task 114: Security Testing."""

import numpy as np
import pytest

from security_audit.security_testing import (
    FuzzSample,
    SecurityTestRunner,
    SecurityTestReport,
    TestCase,
    TestRunResult,
)


@pytest.fixture
def runner():
    return SecurityTestRunner()


def simple_detector(text: str) -> bool:
    dangerous = ["sql", "script", "drop", "exec", "union"]
    return not any(d in text.lower() for d in dangerous)


class TestTestCase:
    def test_case_creation(self):
        tc = TestCase(name="test1", category="injection", input_data="SELECT * FROM users", expected_safe=False)
        assert tc.name == "test1"
        assert tc.expected_safe is False


class TestFuzzSample:
    def test_fuzz_generation_count(self, runner):
        samples = runner.fuzz_generate("SELECT * FROM users WHERE id=1", count=20)
        assert len(samples) == 20

    def test_fuzz_sample_ids_unique(self, runner):
        samples = runner.fuzz_generate("test", count=10)
        ids = [s.sample_id for s in samples]
        assert len(set(ids)) == 10

    def test_fuzz_sample_category(self, runner):
        samples = runner.fuzz_generate("payload", count=5)
        for s in samples:
            assert s.category == "fuzz"


class TestSecurityTestRunner:
    def test_register_test_passes(self, runner):
        tc = TestCase(name="safe", category="safe", input_data="hello world", expected_safe=True)
        runner.register_test(tc, simple_detector)
        assert len(runner._results) == 1
        assert runner._results[0].passed is True

    def test_register_test_fails(self, runner):
        tc = TestCase(name="unsafe", category="injection", input_data="SELECT * FROM users", expected_safe=False)
        runner.register_test(tc, simple_detector)
        assert runner._results[0].passed is False

    def test_run_batch(self, runner):
        cases = [
            TestCase("safe1", "safe", "hello", True),
            TestCase("unsafe1", "injection", "DROP TABLE", False),
        ]
        results = runner.run_batch(cases, simple_detector)
        assert len(results) == 2

    def test_fuzz_test(self, runner):
        samples = runner.fuzz_generate("SELECT * FROM users", count=10)
        results = runner.fuzz_test(simple_detector, samples)
        assert len(results) == 10

    def test_generate_report_structure(self, runner):
        tc = TestCase("t1", "cat", "hello", True)
        runner.register_test(tc, simple_detector)
        report = runner.generate_report()
        assert isinstance(report, SecurityTestReport)
        assert report.total == 1

    def test_report_passed_equals_total_when_all_pass(self, runner):
        cases = [TestCase(f"t{i}", "safe", f"text{i}", True) for i in range(5)]
        runner.run_batch(cases, simple_detector)
        report = runner.generate_report()
        assert report.passed == report.total
        assert report.failed == 0

    def test_coverage_summary(self, runner):
        cases = [
            TestCase("t1", "injection", "DROP TABLE", False),
            TestCase("t2", "xss", "<script>", False),
            TestCase("t3", "safe", "hello", True),
        ]
        runner.run_batch(cases, simple_detector)
        summary = runner.coverage_summary()
        assert summary["total"] == 3
        assert "injection" in summary["categories"]

    def test_fuzz_max_length(self, runner):
        samples = runner.fuzz_generate("A" * 100, count=5, max_length=50)
        for s in samples:
            assert len(s.payload) <= 50


class TestSecurityTestingNumpy:
    def test_report_risk_score_numeric(self, runner):
        cases = [TestCase(f"t{i}", "cat", f"text{i}", True) for i in range(10)]
        runner.run_batch(cases, simple_detector)
        report = runner.generate_report()
        assert isinstance(report.risk_score, float)

    def test_results_array_dtype(self, runner):
        cases = [TestCase(f"t{i}", "cat", f"text{i}", True) for i in range(5)]
        runner.run_batch(cases, simple_detector)
        scores = np.array([1.0 if r.passed else 0.0 for r in runner._results], dtype=np.float64)
        assert scores.dtype in (np.float64, np.float32)

    def test_fuzz_latency_array(self, runner):
        samples = runner.fuzz_generate("test", count=10)
        results = runner.fuzz_test(simple_detector, samples)
        latencies = np.array([r.latency_ms for r in results], dtype=np.float64)
        assert np.all(latencies >= 0.0)

    def test_category_counts_distribution(self, runner):
        cases = [
            TestCase("t1", "injection", "DROP", False),
            TestCase("t2", "injection", "UNION", False),
            TestCase("t3", "safe", "hello", True),
        ]
        runner.run_batch(cases, simple_detector)
        counts = np.array([1 if r.passed else 0 for r in runner._results], dtype=np.int64)
        assert len(counts) == 3
