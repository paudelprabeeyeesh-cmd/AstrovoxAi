from alignment.reward_hacking_detector import RewardHackingDetector


class TestRewardHackingDetector:
    def test_detect_sycophancy(self):
        detector = RewardHackingDetector(threshold=0.5)
        result = detector.detect_sycophancy([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert "score" in result

    def test_detect_verbosity(self):
        detector = RewardHackingDetector(threshold=0.5)
        result = detector.detect_verbosity([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
        assert "score" in result

    def test_detect_evasion(self):
        detector = RewardHackingDetector(threshold=0.5)
        result = detector.detect_evasion([1.0, 2.0, 3.0], [0.0, 1.0, 0.0])
        assert "score" in result

    def test_detect_reward_anomalies(self):
        detector = RewardHackingDetector()
        result = detector.detect_reward_anomalies([0.1, 0.1, 0.1, 100.0])
        assert "max_z" in result

    def test_detect_reward_anomalies_empty(self):
        detector = RewardHackingDetector()
        result = detector.detect_reward_anomalies([])
        assert result["flagged"] is False

    def test_summary(self):
        detector = RewardHackingDetector(threshold=0.5)
        detector.detect_sycophancy([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        detector.detect_verbosity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        summary = detector.summary()
        assert "total_flagged" in summary
