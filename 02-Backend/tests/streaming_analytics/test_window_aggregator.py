from streaming_analytics.window_aggregator import WindowAggregator, Window


FIXTURE_EVENTS = [
    {"type": "page_view", "timestamp": 1.0, "payload": {"duration": 5}},
    {"type": "page_view", "timestamp": 6.0, "payload": {"duration": 3}},
    {"type": "click", "timestamp": 13.0, "payload": {"duration": 1}},
    {"type": "page_view", "timestamp": 18.0, "payload": {"duration": 7}},
]


class TestWindowAggregator:
    def test_tumbling_windows(self):
        agg = WindowAggregator(window_size=10.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        windows = agg.windows()
        assert len(windows) == 2

    def test_sliding_windows(self):
        agg = WindowAggregator(window_size=10.0, slide=5.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        windows = agg.windows()
        assert len(windows) > 1

    def test_get_window(self):
        agg = WindowAggregator(window_size=10.0)
        agg.add_event(FIXTURE_EVENTS[0])
        window = agg.get_window(1.0)
        assert window is not None
        assert window.start == 0.0
        assert window.end == 10.0

    def test_count_by_type(self):
        agg = WindowAggregator(window_size=15.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        counts = agg.count_by_type()
        values = list(counts.values())
        assert any(v.get("page_view") == 2 for v in values)

    def test_sum_field(self):
        agg = WindowAggregator(window_size=15.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        sums = agg.sum_field("duration")
        values = list(sums.values())
        assert any(v.get("page_view") == 8.0 for v in values)

    def test_avg_field(self):
        agg = WindowAggregator(window_size=15.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        avgs = agg.avg_field("duration")
        values = list(avgs.values())
        assert any(abs(v.get("page_view") - 4.0) < 1e-9 for v in values)

    def test_clear(self):
        agg = WindowAggregator(window_size=10.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        agg.clear()
        assert agg.windows() == []

    def test_add_events_batch(self):
        agg = WindowAggregator(window_size=10.0)
        updated = agg.add_events(FIXTURE_EVENTS)
        assert len(updated) == len(FIXTURE_EVENTS)
