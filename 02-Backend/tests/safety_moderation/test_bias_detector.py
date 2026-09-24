from safety_moderation.bias_detector import BiasDetector, BiasReport


class TestBiasDetector:
    def setup_method(self):
        self.detector = BiasDetector(threshold=0.6, seed=321)

    def test_empty_input_no_bias(self):
        report = self.detector.detect("")
        assert report.flagged is False
        assert report.bias_score == 0.0
        assert report.category == "none"

    def test_whitespace_no_bias(self):
        report = self.detector.detect("   ")
        assert report.flagged is False
        assert report.bias_score == 0.0

    def test_batch_detect_length(self):
        texts = ["He is a man", "She is a woman", "Test"]
        reports = self.detector.batch_detect(texts)
        assert len(reports) == len(texts)
        for report in reports:
            assert isinstance(report, BiasReport)

    def test_metrics_present(self):
        report = self.detector.detect("He is a man")
        for cat in BiasDetector.CATEGORIES:
            assert f"{cat}_density" in report.metrics
            assert f"{cat}_raw" in report.metrics

    def test_threshold_update(self):
        self.detector.update_threshold(0.9)
        assert self.detector.threshold == 0.9
        report = self.detector.detect("Some text")
        assert report.flagged is False

    def test_deterministic_output(self):
        d1 = BiasDetector(threshold=0.6, seed=321)
        d2 = BiasDetector(threshold=0.6, seed=321)
        r1 = d1.detect("He is a man")
        r2 = d2.detect("He is a man")
        assert r1.category == r2.category
        assert abs(r1.bias_score - r2.bias_score) < 1e-5

    def test_aggregate_returns_dict(self):
        reports = self.detector.batch_detect(["He is a man", "She is a woman", "Test"])
        agg = self.detector.aggregate(reports)
        assert isinstance(agg, dict)
        assert "mean_bias_score" in agg
        assert "flag_rate" in agg
        assert agg["total"] == 3.0

    def test_aggregate_empty(self):
        agg = self.detector.aggregate([])
        assert agg == {}

    def test_all_categories_represented(self):
        categories = BiasDetector.CATEGORIES
        assert "gender" in categories
        assert "race" in categories
        assert "religion" in categories
        assert "age" in categories
        assert "disability" in categories
        assert "socioeconomic" in categories

    def test_score_in_range(self):
        report = self.detector.detect("Some random text with bias indicators")
        assert 0.0 <= report.bias_score <= 1.0
