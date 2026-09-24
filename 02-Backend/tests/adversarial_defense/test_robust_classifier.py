import math

from adversarial_defense import RobustClassifier


class TestRobustClassifier:
    def test_init_raises_for_invalid_classes(self):
        try:
            RobustClassifier(num_classes=0)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected ValueError")

    def test_train_and_predict(self):
        clf = RobustClassifier(num_classes=2)
        clf.train([[1.0, 2.0], [3.0, 4.0]], [0, 1])
        pred = clf.predict([1.0, 2.0])
        assert pred in [0, 1]

    def test_predict_raises_before_train(self):
        clf = RobustClassifier(num_classes=2)
        try:
            clf.predict([1.0, 2.0])
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected RuntimeError")

    def test_evaluate_returns_accuracy(self):
        clf = RobustClassifier(num_classes=2)
        clf.train([[1.0, 2.0], [3.0, 4.0]], [0, 1])
        acc = clf.evaluate([[1.0, 2.0]], [0])
        assert 0.0 <= acc <= 1.0

    def test_robustness_score(self):
        clf = RobustClassifier(num_classes=2)
        clf.train([[1.0, 2.0], [3.0, 4.0]], [0, 1])
        score = clf.robustness_score([1.0, 2.0])
        assert isinstance(score, float)
        assert math.isfinite(score)
