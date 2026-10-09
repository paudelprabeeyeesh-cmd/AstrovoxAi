import math

from adversarial_defense import CertifiedDefense


class TestCertifiedDefense:
    def test_init_raises_for_non_positive_sigma(self):
        try:
            CertifiedDefense(sigma=0.0)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")

    def test_smoothed_predict(self):
        cd = CertifiedDefense(sigma=0.25, num_samples=64)
        weights = [[1.0, 2.0], [2.0, 1.0]]
        pred = cd.smoothed_predict(weights, [1.0, 2.0])
        assert pred in [0, 1]

    def test_certified_accuracy(self):
        cd = CertifiedDefense(sigma=0.25, num_samples=64)
        weights = [[1.0, 2.0], [2.0, 1.0]]
        acc = cd.certified_accuracy(weights, [[1.0, 2.0]])
        assert 0.0 <= acc <= 1.0

    def test_certified_accuracy_empty_samples(self):
        cd = CertifiedDefense()
        assert cd.certified_accuracy([[1.0]], []) == 0.0

    def test_radius_non_negative(self):
        cd = CertifiedDefense()
        r = cd.radius([30, 34])
        assert isinstance(r, float)
        assert r >= 0.0

    def test_certify(self):
        cd = CertifiedDefense(sigma=0.25, num_samples=64)
        weights = [[1.0, 2.0], [2.0, 1.0]]
        pred, radius = cd.certify(weights, [1.0, 2.0])
        assert pred in [0, 1]
        assert radius >= 0.0

    def test_randomized_smoothing(self):
        cd = CertifiedDefense(sigma=0.25, num_samples=64)
        result = cd.randomized_smoothing([1.0, 2.0])
        assert len(result) == 2
