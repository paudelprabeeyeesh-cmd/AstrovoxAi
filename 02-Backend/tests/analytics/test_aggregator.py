from analytics.aggregator import Aggregator


FIXTURE_EVENTS = [
    {"type": "page_view", "timestamp": 1000.0, "payload": {"duration": 5}},
    {"type": "page_view", "timestamp": 1001.0, "payload": {"duration": 3}},
    {"type": "click", "timestamp": 1002.0, "payload": {"duration": 1}},
    {"type": "page_view", "timestamp": 1003.0, "payload": {"duration": 7}},
]


class TestAggregator:
    def test_count_by_type(self):
        agg = Aggregator()
        result = agg.count_by_type(FIXTURE_EVENTS)
        assert result["page_view"] == 3
        assert result["click"] == 1

    def test_count_by_type_empty(self):
        agg = Aggregator()
        assert agg.count_by_type([]) == {}

    def test_sum_payload_field(self):
        agg = Aggregator()
        result = agg.sum_payload_field(FIXTURE_EVENTS, "duration")
        assert result["page_view"] == 15.0
        assert result["click"] == 1.0

    def test_sum_payload_field_missing(self):
        agg = Aggregator()
        result = agg.sum_payload_field(FIXTURE_EVENTS, "missing_field")
        assert result == {}

    def test_sum_payload_field_non_numeric(self):
        agg = Aggregator()
        events = [{"type": "x", "timestamp": 0, "payload": {"field": "bad"}}]
        result = agg.sum_payload_field(events, "field")
        assert result == {}

    def test_avg_payload_field(self):
        agg = Aggregator()
        result = agg.avg_payload_field(FIXTURE_EVENTS, "duration")
        assert result["page_view"] == 5.0
        assert result["click"] == 1.0

    def test_avg_payload_field_empty(self):
        agg = Aggregator()
        assert agg.avg_payload_field([], "duration") == {}

    def test_group_by_interval(self):
        agg = Aggregator()
        events = [
            {"type": "x", "timestamp": 5.0, "payload": {}},
            {"type": "y", "timestamp": 95.0, "payload": {}},
            {"type": "z", "timestamp": 105.0, "payload": {}},
        ]
        result = agg.group_by_interval(events, 60)
        assert 0 in result
        assert 60 in result
        assert len(result[0]) == 1
        assert len(result[60]) == 2

    def test_group_by_interval_sorted(self):
        agg = Aggregator()
        events = [
            {"type": "x", "timestamp": 200.0, "payload": {}},
            {"type": "y", "timestamp": 100.0, "payload": {}},
        ]
        result = agg.group_by_interval(events, 100)
        keys = list(result.keys())
        assert keys == sorted(keys)

    def test_top_n_types(self):
        agg = Aggregator()
        events = [
            {"type": "a", "timestamp": 0, "payload": {}},
            {"type": "a", "timestamp": 0, "payload": {}},
            {"type": "b", "timestamp": 0, "payload": {}},
            {"type": "c", "timestamp": 0, "payload": {}},
        ]
        top = agg.top_n_types(events, n=2)
        assert top[0][0] == "a"
        assert top[0][1] == 2
        assert len(top) == 2
