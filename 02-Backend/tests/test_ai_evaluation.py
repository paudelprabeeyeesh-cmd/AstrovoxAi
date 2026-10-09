
import pytest
from unittest.mock import patch, MagicMock
from app.evaluation import EvaluationSuite, MetricsCalculator, QualityMetrics, HallucinationDetector, RegressionTester


class TestAIEvaluationSuite:
    def test_evaluation_suite_runs(self):
        suite = EvaluationSuite()
        suite.register_suite("demo", [
            {"prompt": "Hello", "expected": "Hello", "rubric": {"pass_threshold": 0.5}},
        ])
        result = suite.run_suite("demo", lambda p: f"Response to: {p}")
        assert result["total"] == 1
        assert "pass_rate" in result

    def test_evaluation_suite_scores_output(self):
        suite = EvaluationSuite()
        suite.register_suite("demo", [
            {"prompt": "test", "expected": "testing", "rubric": {"pass_threshold": 0.0}},
        ])
        result = suite.run_suite("demo", lambda p: p.upper())
        assert result["results"][0]["score"] >= 0.0

    def test_metrics_calculator(self):
        calc = MetricsCalculator()
        result = calc.calculate("hello world", "hello", "hello world")
        assert "tokens" in result
        assert "coherence" in result
        assert "relevance" in result
        assert "accuracy" in result

    def test_quality_metrics_calculate_relevance(self):
        qm = QualityMetrics()
        score = qm.calculate_relevance("hello world", "hello there")
        assert 0.0 <= score <= 1.0

    def test_quality_metrics_calculate_coherence(self):
        qm = QualityMetrics()
        score = qm.calculate_coherence("First sentence. Second sentence. Third.")
        assert score > 0.0

    def test_quality_metrics_calculate_factuality(self):
        qm = QualityMetrics()
        score = qm.calculate_factuality("hello world", "hello there world")
        assert 0.0 <= score <= 1.0

    def test_hallucination_detector(self):
        detector = HallucinationDetector()
        result = detector.detect("This is definitely always certain", "some context")
        assert "score" in result
        assert "risk_level" in result

    def test_regression_tester(self):
        tester = RegressionTester()
        tester.set_baseline("test1", "expected output")
        result = tester.test("test1", "expected output")
        assert result["passed"] is True
        result2 = tester.test("test1", "different output")
        assert result2["passed"] is False
