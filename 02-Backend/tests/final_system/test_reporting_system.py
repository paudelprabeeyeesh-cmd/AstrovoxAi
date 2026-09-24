import pytest
from final_system.reporting_system import Report, ReportingSystem


def test_generate_and_get_report():
    rs = ReportingSystem()
    report = Report(title="daily", data={"views": 100})
    rs.generate_report(report)
    stored = rs.get_report("daily")
    assert stored.data["views"] == 100
    assert stored.generated_at != ""


def test_dashboard():
    rs = ReportingSystem()
    rs.generate_report(Report(title="r1", data={}))
    rs.generate_report(Report(title="r2", data={}))
    rs.register_dashboard("main", ["r1", "r2"])
    dash = rs.dashboard("main")
    assert "r1" in dash
    assert "r2" in dash


def test_list_reports_and_dashboards():
    rs = ReportingSystem()
    rs.generate_report(Report(title="a", data={}))
    rs.register_dashboard("d1", [])
    assert "a" in rs.list_reports()
    assert "d1" in rs.list_dashboards()


def test_get_missing_report():
    rs = ReportingSystem()
    assert rs.get_report("missing") is None
