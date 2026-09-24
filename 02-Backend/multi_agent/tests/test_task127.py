from multi_agent.task127_livelock import LivelockDetector


class TestLivelockDetector:
    def test_no_livelock(self):
        det = LivelockDetector()
        for i in range(3):
            det.observe(i)
        assert not det.livelock_detected

    def test_livelock(self):
        det = LivelockDetector(progress_fn=lambda s: False)
        for i in range(6):
            det.observe(i)
        assert det.livelock_detected

    def test_reset(self):
        det = LivelockDetector(progress_fn=lambda s: False)
        for i in range(6):
            det.observe(i)
        assert det.livelock_detected
        det.reset()
        assert not det.livelock_detected
        assert det.history == []
