import pytest
from analytics.event_tracker import EventTracker
from analytics.reporter import Reporter


@pytest.fixture
def tracker():
    t = EventTracker()
    t.track("page_view", {"duration": 5})
    t.track("page_view", {"duration": 3})
    t.track("click", {"duration": 1})
    t.track("page_view", {"duration": 7})
    return t


class TestReporter:
    def test_summary_report(self, tracker):
        reporter = Reporter(tracker)
        report = reporter.summary_report()
        assert report["total_events"] == 4
        assert report["counts_by_type"]["page_view"] == 3
        assert report["counts_by_type"]["click"] == 1
        assert len(report["top_types"]) <= 5

    def test_summary_report_filter_by_type(self, tracker):
        reporter = Reporter(tracker)
        report = reporter.summary_report(event_type="page_view")
        assert report["total_events"] == 3
        assert report["counts_by_type"]["page_view"] == 3
        assert "click" not in report["counts_by_type"]

    def test_timeseries_report(self, tracker):
        reporter = Reporter(tracker)
        report = reporter.timeseries_report(interval_seconds=60)
        assert "interval_seconds" in report
        assert report["interval_seconds"] == 60
        assert "buckets" in report

    def test_payload_summary(self, tracker):
        reporter = Reporter(tracker)
        report = reporter.payload_summary("duration")
        assert report["field"] == "duration"
        assert report["sums_by_type"]["page_view"] == 15.0
        assert report["sums_by_type"]["click"] == 1.0
        assert report["avgs_by_type"]["page_view"] == 5.0
        assert report["avgs_by_type"]["click"] == 1.0

    def test_payload_summary_empty_tracker(self):
        reporter = Reporter(EventTracker())
        report = reporter.payload_summary("duration")
        assert report["sums_by_type"] == {}
        assert report["avgs_by_type"] == {}
