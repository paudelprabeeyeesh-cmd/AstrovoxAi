
import pytest
from unittest.mock import patch, MagicMock
from app.analytics import PerformanceReporter


class TestPerformanceReporter:
    @patch("app.analytics.performance_reporter.PROMETHEUS_AVAILABLE", False)
    @patch("app.analytics.performance_reporter.get_organization_analytics")
    def test_generate_report_with_org(self, mock_org_analytics):
        mock_org_analytics.return_value = {"org_id": "org-1", "events": []}
        reporter = PerformanceReporter()
        report = reporter.generate_report(org_id="org-1")
        assert "generated_at" in report
        assert report["org_analytics"]["org_id"] == "org-1"

    @patch("app.analytics.performance_reporter.PROMETHEUS_AVAILABLE", False)
    @patch("app.analytics.performance_reporter.get_user_analytics")
    def test_generate_report_with_user(self, mock_user_analytics):
        mock_user_analytics.return_value = {"user_id": "user-1", "usage": {}}
        reporter = PerformanceReporter()
        report = reporter.generate_report(user_id="user-1")
        assert report["user_analytics"]["user_id"] == "user-1"

    def test_export_json(self):
        reporter = PerformanceReporter()
        report = {"status": "healthy", "summary": {}}
        exported = reporter.export_json(report)
        assert "healthy" in exported

    def test_export_csv(self):
        reporter = PerformanceReporter()
        report = {"summary": {"status": "healthy", "total_requests": 10}}
        exported = reporter.export_csv(report)
        assert "status" in exported
        assert "healthy" in exported
