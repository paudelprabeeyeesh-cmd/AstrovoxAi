
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import TokenTracker


class TestTokenTracker:
    @patch("app.analytics.token_tracker.get_db")
    def test_track_tokens_returns_event_id(self, mock_get_db):
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = TokenTracker()
        event_id = tracker.track_tokens("user-1", "gpt-4o", 100, 50)
        assert event_id is not None

    @patch("app.analytics.token_tracker.get_db")
    def test_get_user_tokens(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchone.return_value = {"total_tokens": 150, "requests": 3}
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = TokenTracker()
        result = tracker.get_user_tokens("user-1")
        assert result["total_tokens"] == 150
        assert result["requests"] == 3

    @patch("app.analytics.token_tracker.get_db")
    def test_get_token_trend(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"day": "2024-01-01", "tokens": 500, "requests": 5}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = TokenTracker()
        result = tracker.get_token_trend()
        assert isinstance(result, list)

    @patch("app.analytics.token_tracker.get_db")
    def test_get_model_token_breakdown(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"model": "gpt-4o", "tokens": 1000, "requests": 20}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = TokenTracker()
        result = tracker.get_model_token_breakdown()
        assert result[0]["model"] == "gpt-4o"
