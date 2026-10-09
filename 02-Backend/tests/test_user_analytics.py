
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import UserAnalyticsService


class TestUserAnalyticsService:
    @patch("app.analytics.user_analytics.get_user_analytics")
    def test_get_user_dashboard(self, mock_get_user_analytics):
        mock_get_user_analytics.return_value = {"user_id": "user-1", "events": [], "usage": {}}
        service = UserAnalyticsService()
        result = service.get_user_dashboard("user-1")
        assert result["user_id"] == "user-1"

    @patch("app.analytics.user_analytics.get_db")
    def test_get_user_activity_timeline(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = []
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = UserAnalyticsService()
        result = service.get_user_activity_timeline("user-1")
        assert isinstance(result, list)

    @patch("app.analytics.user_analytics.get_db")
    def test_get_user_retention(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchone.side_effect = [
            {"first": "2024-01-01"},
            {"last": "2024-01-15"},
            {"cnt": 50},
        ]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = UserAnalyticsService()
        result = service.get_user_retention("user-1")
        assert result["first_seen"] == "2024-01-01"
        assert result["total_events"] == 50
