
import pytest
from unittest.mock import patch, MagicMock
from app.pen_test import PenTestSuite


class TestSecurityRedTeam:
    def test_sql_injection_payload_blocked(self):
        suite = PenTestSuite()
        payloads = ["' OR '1'='1", "'; DROP TABLE users; --", "' UNION SELECT NULL--"]
        for payload in payloads:
            with patch.object(suite.session, 'get') as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 400
                mock_resp.text = "Invalid request"
                mock_get.return_value = mock_resp
                result = suite.test_sql_injection("http://localhost:8000/auth/login")
                assert result.status.value == "pass"

    def test_xss_payload_reflected(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<script>alert(1)</script>"
            mock_get.return_value = mock_resp
            result = suite.test_xss("http://localhost:8000/search")
            assert result.status.value == "fail"

    def test_auth_bypass_attempts(self):
        suite = PenTestSuite()
        bypass_attempts = [
            {"headers": {"Authorization": "Bearer "}},
            {"headers": {"Authorization": "Bearer invalid"}},
            {"cookies": {"session": "admin"}},
        ]
        for attempt in bypass_attempts:
            with patch.object(suite.session, 'get') as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 401
                mock_get.return_value = mock_resp
                result = suite.test_auth_bypass("http://localhost:8000/admin")
                assert result.status.value == "pass"

    def test_rate_limit_enforced(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_get.return_value = mock_resp
            result = suite.test_rate_limit("http://localhost:8000/auth/login")
            assert result.status.value == "pass"

    def test_pen_test_full_scan_structure(self):
        suite = PenTestSuite()
        with patch.object(suite.session, 'get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_get.return_value = mock_resp
            report = suite.run_full_scan("http://localhost:8000")
            assert len(report.results) > 0
            assert report.base_url == "http://localhost:8000"
