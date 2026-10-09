from analytics.event_tracker import EventTracker


class TestEventTracker:
    def test_track_returns_event_dict(self):
        tracker = EventTracker()
        event = tracker.track("page_view", {"page": "/home"})
        assert event["type"] == "page_view"
        assert event["payload"] == {"page": "/home"}
        assert "timestamp" in event

    def test_track_default_payload(self):
        tracker = EventTracker()
        event = tracker.track("click")
        assert event["payload"] == {}

    def test_count_empty(self):
        tracker = EventTracker()
        assert tracker.count() == 0
        assert tracker.count("page_view") == 0

    def test_count_after_tracking(self):
        tracker = EventTracker()
        tracker.track("page_view")
        tracker.track("page_view")
        tracker.track("click")
        assert tracker.count() == 3
        assert tracker.count("page_view") == 2
        assert tracker.count("click") == 1

    def test_get_events_filter_by_type(self):
        tracker = EventTracker()
        tracker.track("page_view")
        tracker.track("click")
        tracker.track("page_view")
        results = tracker.get_events(event_type="page_view")
        assert len(results) == 2
        assert all(e["type"] == "page_view" for e in results)

    def test_get_events_filter_by_time_range(self):
        tracker = EventTracker()
        early = tracker.track("click")["timestamp"]
        import time
        time.sleep(0.01)
        tracker.track("page_view")
        late = tracker.track("click")["timestamp"]

        results = tracker.get_events(since=early + 0.005, until=late - 0.005)
        assert all(early + 0.005 <= e["timestamp"] <= late - 0.005 for e in results)

    def test_get_events_empty_when_no_match(self):
        tracker = EventTracker()
        tracker.track("page_view")
        assert tracker.get_events(event_type="nonexistent") == []

    def test_clear(self):
        tracker = EventTracker()
        tracker.track("page_view")
        tracker.track("click")
        tracker.clear()
        assert tracker.count() == 0

    def test_thread_safety(self):
        import threading
        tracker = EventTracker()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    tracker.track("thread_event")
            except Exception as _e:  # noqa: BLE001
                errors.append(_e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert tracker.count() == 400
