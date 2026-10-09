
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import CostTracker


class TestCostTracker:
    @patch("app.analytics.cost_tracker.get_db")
    def test_record_cost_returns_event_id(self, mock_get_db):
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = CostTracker()
        event_id = tracker.record_cost("user-1", "gpt-4o", 100, 50, 0.001)
        assert event_id is not None
        assert len(event_id) > 0

    @patch("app.analytics.cost_tracker.get_db")
    def test_get_user_cost_returns_dict(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchone.return_value = {"total_cost": 1.5, "requests": 10}
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = CostTracker()
        result = tracker.get_user_cost("user-1")
        assert "user_id" in result
        assert result["total_cost"] == 1.5
        assert result["requests"] == 10

    @patch("app.analytics.cost_tracker.get_db")
    def test_get_cost_trend(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"day": "2024-01-01", "cost": 0.5, "requests": 5}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = CostTracker()
        result = tracker.get_cost_trend()
        assert isinstance(result, list)
        assert len(result) == 1

    @patch("app.analytics.cost_tracker.get_db")
    def test_get_model_cost_breakdown(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"model": "gpt-4o", "cost": 1.0, "requests": 10}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        tracker = CostTracker()
        result = tracker.get_model_cost_breakdown()
        assert isinstance(result, list)
        assert result[0]["model"] == "gpt-4o"
