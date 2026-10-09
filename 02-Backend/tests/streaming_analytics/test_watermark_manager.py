from streaming_analytics.watermark_manager import WatermarkManager


class TestWatermarkManager:
    def test_initial_watermark(self):
        wm = WatermarkManager()
        assert wm.watermark() == float("-inf")

    def test_update_watermark(self):
        wm = WatermarkManager()
        wm.update_watermark(5.0)
        assert wm.watermark() == 5.0

    def test_watermark_does_not_decrease(self):
        wm = WatermarkManager()
        wm.update_watermark(10.0)
        wm.update_watermark(3.0)
        assert wm.watermark() == 10.0

    def test_is_late_without_lateness(self):
        wm = WatermarkManager(max_lateness=0.0)
        wm.update_watermark(10.0)
        assert wm.is_late(5.0) is True
        assert wm.is_late(10.0) is False
        assert wm.is_late(15.0) is False

    def test_is_late_with_max_lateness(self):
        wm = WatermarkManager(max_lateness=2.0)
        wm.update_watermark(10.0)
        assert wm.is_late(7.0) is True
        assert wm.is_late(8.0) is False
        assert wm.is_late(10.0) is False

    def test_record_event(self):
        wm = WatermarkManager()
        wm.record_event("click")
        wm.record_event("click")
        wm.record_event("page_view")
        assert wm.total_event_count("click") == 2
        assert wm.total_event_count("page_view") == 1

    def test_record_late(self):
        wm = WatermarkManager()
        wm.record_event("click")
        wm.record_late("click")
        assert wm.late_count("click") == 1
        assert wm.late_ratio("click") == 1.0

    def test_late_ratio_zero_events(self):
        wm = WatermarkManager()
        assert wm.late_ratio("click") == 0.0

    def test_advance(self):
        wm = WatermarkManager()
        result = wm.advance(5.0)
        assert result["previous_watermark"] == float("-inf")
        assert result["current_watermark"] == 5.0
        assert result["advanced"] is True

    def test_advance_no_change(self):
        wm = WatermarkManager()
        wm.update_watermark(10.0)
        result = wm.advance(5.0)
        assert result["advanced"] is False
        assert result["current_watermark"] == 10.0
