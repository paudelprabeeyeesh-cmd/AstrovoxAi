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

    def test_aggregate_custom_func(self):
        agg = WindowAggregator(window_size=15.0)
        for event in FIXTURE_EVENTS:
            agg.add_event(event)
        result = agg.aggregate(lambda events: len(events))
        values = list(result.values())
        assert any(v == 2 for v in values)

    def test_get_window_missing(self):
        agg = WindowAggregator(window_size=10.0)
        agg.add_event(FIXTURE_EVENTS[0])
        assert agg.get_window(100.0) is None

    def test_sum_field_invalid_payload(self):
        agg = WindowAggregator(window_size=15.0)
        events = [
            {"type": "click", "timestamp": 1.0, "payload": {"duration": "bad"}},
            {"type": "click", "timestamp": 2.0, "payload": {}},
        ]
        for event in events:
            agg.add_event(event)
        sums = agg.sum_field("duration")
        assert sums == {} or all(v.get("click", 0) == 0 for v in sums.values())

    def test_avg_field_single_event(self):
        agg = WindowAggregator(window_size=10.0)
        agg.add_event({"type": "click", "timestamp": 1.0, "payload": {"duration": 4}})
        avgs = agg.avg_field("duration")
        assert any(abs(v.get("click") - 4.0) < 1e-9 for v in avgs.values())

    def test_count_by_type_empty(self):
        agg = WindowAggregator(window_size=10.0)
        assert agg.count_by_type() == {}

    def test_window_boundary_exact(self):
        agg = WindowAggregator(window_size=10.0)
        agg.add_event({"type": "click", "timestamp": 10.0, "payload": {}})
        windows = agg.windows()
        assert len(windows) == 1
        assert windows[0].start == 10.0
        assert windows[0].end == 20.0

    def test_sliding_window_overlap(self):
        agg = WindowAggregator(window_size=10.0, slide=5.0)
        agg.add_event({"type": "click", "timestamp": 3.0, "payload": {}})
        agg.add_event({"type": "click", "timestamp": 7.0, "payload": {}})
        windows = agg.windows()
        assert len(windows) == 2
