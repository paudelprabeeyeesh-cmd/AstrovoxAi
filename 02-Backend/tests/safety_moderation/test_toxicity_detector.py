from safety_moderation.toxicity_detector import ToxicityDetector, ToxicityReport


class TestToxicityDetector:
    def setup_method(self):
        self.detector = ToxicityDetector(threshold=0.5, seed=123)

    def test_clean_input_not_flagged(self):
        report = self.detector.detect("What is the weather today?")
        assert report.flagged is False
        assert report.label == "clean"
        assert 0.0 <= report.score <= 1.0

    def test_empty_input_clean(self):
        report = self.detector.detect("")
        assert report.flagged is False
        assert report.label == "clean"
        assert report.score == 0.0

    def test_whitespace_input_clean(self):
        report = self.detector.detect("   ")
        assert report.flagged is False
        assert report.label == "clean"

    def test_batch_detect_length(self):
        texts = ["Hello", "Bad stuff", "Test"]
        reports = self.detector.batch_detect(texts)
        assert len(reports) == len(texts)
        for report in reports:
            assert isinstance(report, ToxicityReport)

    def test_categories_present(self):
        report = self.detector.detect("Some text")
        for label in ToxicityDetector.LABELS:
            assert label in report.categories

    def test_summary_returns_dict(self):
        reports = self.detector.batch_detect(["Hello", "Bad stuff", "Another"])
        summary = self.detector.summary(reports)
        assert isinstance(summary, dict)
        assert "mean_score" in summary
        assert "flag_rate" in summary
        assert summary["total"] == 3.0

    def test_summary_empty(self):
        summary = self.detector.summary([])
        assert summary == {}

    def test_threshold_update(self):
        self.detector.update_threshold(0.9)
        assert self.detector.threshold == 0.9
        report = self.detector.detect("Some text")
        assert report.flagged is False

    def test_deterministic_output(self):
        d1 = ToxicityDetector(threshold=0.5, seed=123)
        d2 = ToxicityDetector(threshold=0.5, seed=123)
        r1 = d1.detect("Consistent text input")
        r2 = d2.detect("Consistent text input")
        assert r1.label == r2.label
        assert abs(r1.score - r2.score) < 1e-5

    def test_all_labels_represented(self):
        labels = ToxicityDetector.LABELS
        assert "clean" in labels
        assert "toxic" in labels
        assert "severe_toxic" in labels
        assert "obscene" in labels
        assert "threat" in labels
        assert "insult" in labels
        assert "identity_hate" in labels
