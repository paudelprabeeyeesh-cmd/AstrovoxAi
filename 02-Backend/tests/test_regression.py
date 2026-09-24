
import pytest
from unittest.mock import patch, MagicMock
from app.evaluation.regression import RegressionTester
from app.evaluation.evaluation_suite import EvaluationSuite
from app.main import app
from fastapi.testclient import TestClient


class TestRegressionTests:
    def setup_method(self):
        self.tester = RegressionTester()

    def test_baseline_set_and_match(self):
        self.tester.set_baseline("greeting", "Hello World")
        result = self.tester.test("greeting", "Hello World")
        assert result["passed"] is True

    def test_baseline_set_and_mismatch(self):
        self.tester.set_baseline("greeting", "Hello World")
        result = self.tester.test("greeting", "Goodbye World")
        assert result["passed"] is False

    def test_empty_baseline(self):
        result = self.tester.test("missing", "anything")
        assert result["passed"] is False

    def test_whitespace_stripped(self):
        self.tester.set_baseline("test", "  expected  ")
        result = self.tester.test("test", "expected")
        assert result["passed"] is True

    def test_regression_integration_health(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_regression_integration_root(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        assert "ASTRAVOX" in response.json()["message"]
