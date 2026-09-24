import numpy as np
import pytest
from emergent_abilities.cross_lingual import MultilingualEmergenceTracker, CrossLingualTransferAnalyzer


class TestMultilingualEmergenceTracker:
    def test_record_performance(self):
        tracker = MultilingualEmergenceTracker(languages=["en", "fr", "de"])
        tracker.record_performance("en", 0.8)
        assert len(tracker.performance_history["en"]) == 1

    def test_compute_transfer(self):
        tracker = MultilingualEmergenceTracker(languages=["en", "fr"])
        for i in range(10):
            tracker.record_performance("en", 0.5 + i * 0.03)
            tracker.record_performance("fr", 0.2 + i * 0.05)
        transfer = tracker.compute_transfer("en", "fr")
        assert transfer > 0.0

    def test_positive_transfer_languages(self):
        tracker = MultilingualEmergenceTracker(languages=["en", "fr", "es"])
        for i in range(10):
            tracker.record_performance("en", 0.5 + i * 0.03)
            tracker.record_performance("fr", 0.2 + i * 0.08)
        tracker.compute_transfer("en", "fr")
        positives = tracker.positive_transfer_languages("fr")
        assert "en" in positives

    def test_interference_detection(self):
        tracker = MultilingualEmergenceTracker(languages=["en", "fr"])
        for i in range(10):
            tracker.record_performance("en", 0.9 - i * 0.03)
            tracker.record_performance("fr", 0.3 + i * 0.05)
        interference = tracker.interference_detection("en", "fr")
        assert interference >= 0.0


class TestCrossLingualTransferAnalyzer:
    def test_compute_transfer_matrix(self):
        analyzer = CrossLingualTransferAnalyzer(source_languages=["en", "fr"], target_languages=["de", "es"])
        perf = {"mono_en": 0.9, "mono_fr": 0.7, "mono_de": 0.6, "mono_es": 0.5}
        matrix = analyzer.compute_transfer_matrix(perf)
        assert matrix.shape == (2, 2)
        assert np.all(np.isfinite(matrix))

    def test_compute_language_connectivity(self):
        analyzer = CrossLingualTransferAnalyzer(source_languages=["en", "fr", "es"], target_languages=["de", "it", "pt"])
        matrix = np.random.rand(3, 3)
        connectivity = analyzer.compute_language_connectivity(matrix)
        assert 0.0 <= connectivity <= 1.0

    def test_transfer_scores_stored(self):
        analyzer = CrossLingualTransferAnalyzer(source_languages=["en"], target_languages=["fr"])
        perf = {"mono_en": 0.8, "mono_fr": 0.5}
        analyzer.compute_transfer_matrix(perf)
        assert ("en", "fr") in analyzer.transfer_scores
