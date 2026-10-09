
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import FeatureAnalyticsService


class TestFeatureAnalyticsService:
    @patch("app.analytics.feature_analytics.get_db")
    def test_track_feature_use_returns_event_id(self, mock_get_db):
        mock_conn = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = FeatureAnalyticsService()
        event_id = service.track_feature_use("user-1", "chat")
        assert event_id is not None
        assert len(event_id) > 0

    @patch("app.analytics.feature_analytics.get_db")
    def test_get_feature_usage(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchall.return_value = [{"feature": "chat", "count": 10}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = FeatureAnalyticsService()
        result = service.get_feature_usage()
        assert "features" in result
        assert result["features"][0]["feature"] == "chat"

    @patch("app.analytics.feature_analytics.get_db")
    def test_get_feature_adoption(self, mock_get_db):
        mock_conn = MagicMock()
        mock_conn.fetchone.return_value = {"cnt": 100}
        mock_conn.fetchall.return_value = [{"feature": "chat", "users": 50}]
        mock_get_db.return_value.__enter__.return_value = mock_conn
        service = FeatureAnalyticsService()
        result = service.get_feature_adoption()
        assert result["total_users"] == 100
        assert result["features"][0]["adoption_rate"] == 0.5
