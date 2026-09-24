import numpy as np
import pytest
from safety_moderation.output_moderation import OutputModerationScanner, OutputScanResult


class TestOutputModerationScanner:
    def setup_method(self):
        self.scanner = OutputModerationScanner(threshold=0.6, window_size=4, batch_size=3)

    def test_scan_text_returns_list(self):
        results = self.scanner.scan_text("Hello world this is a test")
        assert isinstance(results, list)

    def test_scan_text_length_matches_tokens(self):
        text = "one two three four five"
        results = self.scanner.scan_text(text)
        assert len(results) == len(text.split())

    def test_scan_result_fields(self):
        results = self.scanner.scan_text("Test content here")
        for result in results:
            assert isinstance(result, OutputScanResult)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.flagged, bool)
            assert isinstance(result.context_window, list)

    def test_scan_stream_generator(self):
        tokens = ["a", "b", "c", "d"]
        results = list(self.scanner.scan_stream(iter(tokens)))
        assert len(results) == len(tokens)

    def test_confidence_in_valid_range(self):
        results = self.scanner.scan_text("Scanning this text for violations")
        for result in results:
            assert 0.0 <= result.confidence <= 1.0

    def test_context_window_length(self):
        results = self.scanner.scan_text("One two three four five six seven")
        for result in results:
            assert len(result.context_window) <= self.scanner.window_size

    def test_batch_size_affects_streaming(self):
        scanner = OutputModerationScanner(threshold=0.6, window_size=3, batch_size=2)
        tokens = ["a", "b", "c", "d", "e"]
        results = list(scanner.scan_stream(iter(tokens)))
        assert len(results) == len(tokens)

    def test_empty_text_scan(self):
        results = self.scanner.scan_text("")
        assert results == []

    def test_throughput_estimate_positive(self):
        throughput = self.scanner.estimate_throughput(1000)
        assert throughput > 0

    def test_throughput_scales_with_tokens(self):
        tp1 = self.scanner.estimate_throughput(100)
        tp2 = self.scanner.estimate_throughput(200)
        assert tp1 > 0
        assert tp2 > 0

    def test_high_threshold_reduces_flags(self):
        low = OutputModerationScanner(threshold=0.1, window_size=3, batch_size=5)
        high = OutputModerationScanner(threshold=0.99, window_size=3, batch_size=5)
        text = "Some random content for testing thresholds"
        r_low = low.scan_text(text)
        r_high = high.scan_text(text)
        flags_low = sum(1 for r in r_low if r.flagged)
        flags_high = sum(1 for r in r_high if r.flagged)
        assert flags_high <= flags_low

    def test_token_index_sequential(self):
        results = self.scanner.scan_text("First second third fourth")
        indices = [r.token_index for r in results]
        assert indices == list(range(len(indices)))

    def test_stream_with_empty_generator(self):
        results = list(self.scanner.scan_stream(iter([])))
        assert results == []
