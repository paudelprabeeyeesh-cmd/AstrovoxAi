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

    def test_sigmoid_at_zero(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        assert abs(d._sigmoid(0.0) - 0.5) < 1e-5

    def test_sigmoid_positive(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        assert d._sigmoid(100.0) > 0.99

    def test_sigmoid_negative(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        assert d._sigmoid(-100.0) < 0.01

    def test_softmax_sums_to_one(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        scores = {"a": 1.0, "b": 2.0, "c": 3.0}
        probs = d._softmax(scores)
        assert abs(sum(probs.values()) - 1.0) < 1e-5

    def test_token_features_counts_keywords(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        features = d._token_features("hate kill stupid badword1")
        assert features["severe_toxic"] == 2.0
        assert features["insult"] == 1.0
        assert features["obscene"] == 1.0

    def test_detect_with_keyword_text(self):
        d = ToxicityDetector(threshold=0.1, seed=123)
        report = d.detect("hate kill")
        assert report.flagged is True
        assert report.label != "clean"

    def test_deterministic_with_seed(self):
        d1 = ToxicityDetector(threshold=0.5, seed=42)
        d2 = ToxicityDetector(threshold=0.5, seed=42)
        r1 = d1.detect("test input")
        r2 = d2.detect("test input")
        assert r1.score == r2.score
        assert r1.label == r2.label

    def test_batch_detect_empty(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        reports = d.batch_detect([])
        assert reports == []

    def test_threshold_changes_flagging(self):
        d = ToxicityDetector(threshold=0.01, seed=123)
        report = d.detect("hate")
        assert report.flagged is True
        d.update_threshold(0.99)
        report2 = d.detect("hate")
        assert report2.flagged is False

    def test_summary_all_flagged(self):
        d = ToxicityDetector(threshold=0.1, seed=123)
        reports = d.batch_detect(["hate", "kill", "stupid"])
        summary = d.summary(reports)
        assert summary["flag_rate"] == 1.0

    def test_categories_contains_all_labels(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        report = d.detect("Some text")
        for label in ToxicityDetector.LABELS:
            assert label in report.categories

    def test_detect_obscene_keyword(self):
        d = ToxicityDetector(threshold=0.1, seed=123)
        report = d.detect("badword1")
        assert report.label != "clean"

    def test_token_features_no_keywords(self):
        d = ToxicityDetector(threshold=0.5, seed=123)
        features = d._token_features("neutral safe words here")
        for label in ToxicityDetector.LABELS:
            assert features[label] == 0.0

    def test_summary_all_clean(self):
        d = ToxicityDetector(threshold=0.9, seed=123)
        reports = d.batch_detect(["hello", "world", "safe"])
        summary = d.summary(reports)
        assert summary["flag_rate"] == 0.0
        assert summary["mean_score"] == 0.0
