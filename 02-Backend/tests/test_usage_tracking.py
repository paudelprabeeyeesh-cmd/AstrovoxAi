
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import UsageTracker, CostTracker, TokenTracker


class TestUsageTracker:
    @patch("app.analytics.usage_tracker.get_db")
    def test_track_usage_returns_event_id(self, mock_get_db):
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = UsageTracker()
        event_id = tracker.track_usage("user-1", "login")
        assert event_id is not None
        assert len(event_id) > 0

    @patch("app.analytics.usage_tracker.get_db")
    def test_get_user_usage_returns_dict(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = []
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = UsageTracker()
        result = tracker.get_user_usage("user-1")
        assert "user_id" in result
        assert result["user_id"] == "user-1"

    @patch("app.analytics.usage_tracker.get_db")
    def test_get_top_usage_actions(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"action": "login", "count": 10}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = UsageTracker()
        result = tracker.get_top_usage_actions()
        assert isinstance(result, list)
