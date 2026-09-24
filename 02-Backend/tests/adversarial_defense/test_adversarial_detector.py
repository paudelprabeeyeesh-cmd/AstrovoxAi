import math

from adversarial_defense import AdversarialDetector


class TestAdversarialDetector:
    def test_fit_computes_baseline_norm(self):
        detector = AdversarialDetector()
        detector.fit([[1.0, 2.0], [2.0, 3.0]])
        assert detector._fitted is True

    def test_l2_norm(self):
        detector = AdversarialDetector()
        assert math.isclose(detector.l2_norm([1.0, 2.0]), math.sqrt(5.0))

    def test_detect_returns_bool_and_float(self):
        detector = AdversarialDetector()
        detector.fit([[1.0, 2.0]])
        is_adv, score = detector.detect([1.0, 2.0])
        assert isinstance(is_adv, bool)
        assert isinstance(score, float)

    def test_detect_raises_before_fit(self):
        detector = AdversarialDetector()
        try:
            detector.detect([1.0, 2.0])
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")

    def test_batch_detect(self):
        detector = AdversarialDetector()
        detector.fit([[1.0, 2.0]])
        results = detector.batch_detect([[1.0, 2.0], [10.0, 10.0]])
        assert len(results) == 2

    def test_is_adversarial_returns_bool(self):
        detector = AdversarialDetector()
        detector.fit([[1.0, 2.0]])
        assert isinstance(detector.is_adversarial([1.0, 2.0]), bool)
