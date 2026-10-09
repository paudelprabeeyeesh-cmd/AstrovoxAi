


class TestDashboardModule:
    def test_dashboard_panels_non_empty(self):
        from app.dashboard import DASHBOARD_PANELS

        assert len(DASHBOARD_PANELS) > 0
        panel_ids = [p["id"] for p in DASHBOARD_PANELS]
        assert len(panel_ids) == len(set(panel_ids)), "Panel IDs must be unique"

    def test_get_dashboard_returns_dict(self):
        from app.dashboard import get_dashboard

        result = get_dashboard()
        assert isinstance(result, dict)
        assert "dashboard" in result
        assert "health" in result
        assert "metrics_available" in result
        assert "generated_at" in result

    def test_get_dashboard_panels_preserved(self):
        from app.dashboard import DASHBOARD_PANELS, get_dashboard

        result = get_dashboard()
        assert result["dashboard"]["panels"] == DASHBOARD_PANELS

    def test_metrics_summary_returns_dict(self):
        from app.dashboard import metrics_summary

        result = metrics_summary()
        assert isinstance(result, dict)

    def test_dashboard_panels_have_required_fields(self):
        from app.dashboard import DASHBOARD_PANELS

        for panel in DASHBOARD_PANELS:
            assert "id" in panel
            assert "title" in panel
            assert "type" in panel
            assert "targets" in panel
