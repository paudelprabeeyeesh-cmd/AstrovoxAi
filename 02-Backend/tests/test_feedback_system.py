
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import FeedbackAnalyticsService


class TestFeedbackAnalyticsService:
    @patch("app.analytics.feedback_analytics.get_db")
    @patch("app.analytics.feedback_analytics.create_feedback")
    def test_record_feedback(self, mock_create_feedback, mock_get_db):
        mock_fb = MagicMock()
        mock_fb.id = "fb-1"
        mock_fb.rating = 5
        mock_fb.comment = "Great"
        mock_fb.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_create_feedback.return_value = mock_fb
        service = FeedbackAnalyticsService()
        result = service.record_feedback("user-1", "req-1", 5, "Great")
        assert result["id"] == "fb-1"
        assert result["rating"] == 5

    @patch("app.analytics.feedback_analytics.get_db")
    def test_get_feedback_summary(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"rating": 5, "count": 10}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = FeedbackAnalyticsService()
        result = service.get_feedback_summary()
        assert "total_feedback" in result
        assert "average_rating" in result

    @patch("app.analytics.feedback_analytics.get_db")
    def test_get_recent_feedback(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"id": "fb-1", "rating": 5}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = FeedbackAnalyticsService()
        result = service.get_recent_feedback()
        assert isinstance(result, list)
