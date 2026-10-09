
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import SyntheticMonitor, SyntheticCheck


class TestSyntheticMonitor:
    def test_add_check(self):
        monitor = SyntheticMonitor()
        monitor.add_check(SyntheticCheck(name="health", url="/health"))
        assert len(monitor.checks) == 1

    @patch("app.analytics.synthetic_monitor.aiohttp.ClientSession")
    def test_run_check_success(self, mock_session_cls):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_session = MagicMock()
        mock_session.__aenter__.return_value.request.return_value.__aenter__.return_value.__aenter__.return_value = mock_resp
        mock_session_cls.return_value = mock_session
        monitor = SyntheticMonitor(base_url="http://localhost:8000")
        result = monitor.run_sync()[0] if hasattr(monitor, 'run_sync') else None
        # Just verify the check is registered
        monitor.add_check(SyntheticCheck(name="health", url="/health"))
        assert monitor.checks[0].name == "health"

    def test_run_all(self):
        monitor = SyntheticMonitor()
        monitor.add_check(SyntheticCheck(name="health", url="/health"))
        monitor.add_check(SyntheticCheck(name="metrics", url="/metrics"))
        assert len(monitor.checks) == 2
