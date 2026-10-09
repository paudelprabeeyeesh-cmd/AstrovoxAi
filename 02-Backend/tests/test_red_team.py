
import pytest
from unittest.mock import patch, MagicMock
from app.pen_test import PenTestSuite, TestReport


class TestRedTeamSecurity:
    def test_pen_test_sql_injection_detection(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "sql syntax error"
            mock_get.return_value = mock_resp
            result = suite.test_sql_injection("http://localhost:8000/auth/login")
            assert result.test_name == "sql_injection"

    def test_pen_test_xss_detection(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<script>alert(1)</script>"
            mock_get.return_value = mock_resp
            result = suite.test_xss("http://localhost:8000/search")
            assert result.test_name == "xss"

    def test_pen_test_auth_bypass(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            result = suite.test_auth_bypass("http://localhost:8000/admin")
            assert result.test_name == "auth_bypass"

    def test_pen_test_rate_limit(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_get.return_value = mock_resp
            result = suite.test_rate_limit("http://localhost:8000/auth/login")
            assert result.test_name == "rate_limit"
            assert result.status.value == "pass"

    def test_pen_test_full_scan(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            report = suite.run_full_scan("http://localhost:8000")
            assert isinstance(report, TestReport)
            assert report.base_url == "http://localhost:8000"
