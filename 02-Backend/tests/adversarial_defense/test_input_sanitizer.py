import math

from adversarial_defense import InputSanitizer


class TestInputSanitizer:
    def test_l2_norm(self):
        sanitizer = InputSanitizer()
        assert math.isclose(sanitizer.l2_norm([1.0, 2.0]), math.sqrt(5.0))

    def test_clip(self):
        sanitizer = InputSanitizer()
        assert sanitizer.clip([1.0, 5.0], 2.0) == [1.0, 2.0]

    def test_normalize(self):
        sanitizer = InputSanitizer()
        norm = sanitizer.normalize([1.0, 2.0])
        assert math.isclose(sanitizer.l2_norm(norm), 1.0)

    def test_normalize_zero_vector(self):
        sanitizer = InputSanitizer()
        assert sanitizer.normalize([0.0, 0.0]) == [0.0, 0.0]

    def test_sanitize_per_feature(self):
        sanitizer = InputSanitizer(per_feature=True, clip_value=2.0)
        result = sanitizer.sanitize([10.0, 10.0])
        assert all(abs(v) <= 2.0 for v in result)

    def test_batch_sanitize(self):
        sanitizer = InputSanitizer()
        batch = sanitizer.batch_sanitize([[1.0, 2.0], [10.0, 10.0]])
        assert len(batch) == 2

    def test_feature_stats(self):
        sanitizer = InputSanitizer()
        means, sdevs = sanitizer.feature_stats([[1.0, 2.0], [3.0, 4.0]])
        assert len(means) == 2
        assert len(sdevs) == 2

    def test_feature_stats_raises_for_empty(self):
        sanitizer = InputSanitizer()
        try:
            sanitizer.feature_stats([])
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")

    def test_filter_outliers(self):
        sanitizer = InputSanitizer()
        filtered = sanitizer.filter_outliers([1.0, 2.0, 3.0])
        assert len(filtered) == 3
