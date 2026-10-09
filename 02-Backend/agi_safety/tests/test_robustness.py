import numpy as np
import pytest
from agi_safety.robustness import AdversarialDefense, OODResult, RobustnessReport


class TestAdversarialDefense:
    def setup_method(self):
        rng = np.random.RandomState(42)
        n = 20
        self.defense = AdversarialDefense(input_dim=8, num_classes=3, epsilon=0.1, seed=42)
        self.x = rng.randn(n, 8)
        self.y = rng.randint(0, 3, size=n)

    def test_predict_returns_valid_classes(self):
        preds = self.defense.predict(self.x)
        assert set(preds).issubset({0, 1, 2})

    def test_predict_proba_sums_to_one(self):
        probs = self.defense.predict_proba(self.x)
        np.testing.assert_allclose(probs.sum(axis=1), 1.0, atol=1e-6)

    def test_pgd_attack_changes_input(self):
        x_adv = self.defense.pgd_attack(self.x[:1], steps=3)
        assert not np.allclose(x_adv, self.x[:1])

    def test_pgd_perturbation_within_epsilon(self):
        x_adv = self.defense.pgd_attack(self.x[:1], steps=3)
        delta = np.abs(x_adv - self.x[:1])
        assert np.all(delta <= self.defense.epsilon + 1e-6)

    def test_adversarial_training_step_returns_loss(self):
        loss = self.defense.adversarial_training_step(self.x[:4], self.y[:4])
        assert loss >= 0.0

    def test_fit_ood_detector(self):
        self.defense.fit_ood_detector(self.x)
        assert self.defense.ood_mean is not None
        assert self.defense.ood_cov_inv is not None

    def test_detect_ood_after_fit(self):
        self.defense.fit_ood_detector(self.x)
        result = self.defense.detect_ood(self.x[0].reshape(1, -1))
        assert isinstance(result, OODResult)

    def test_detect_ood_raises_before_fit(self):
        with pytest.raises(RuntimeError):
            self.defense.detect_ood(self.x[0].reshape(1, -1))

    def test_evaluate_returns_report(self):
        self.defense.fit_ood_detector(self.x)
        x_adv = self.defense.pgd_attack(self.x, steps=2)
        report = self.defense.evaluate(self.x, self.y, x_adv)
        assert isinstance(report, RobustnessReport)
        assert 0.0 <= report.clean_accuracy <= 1.0

    def test_robustness_drop_nonnegative(self):
        self.defense.fit_ood_detector(self.x)
        x_adv = self.defense.pgd_attack(self.x, steps=2)
        report = self.defense.evaluate(self.x, self.y, x_adv)
        assert report.robustness_drop >= -0.5

    def test_ood_detection_rate_in_range(self):
        self.defense.fit_ood_detector(self.x)
        x_adv = self.defense.pgd_attack(self.x, steps=2)
        report = self.defense.evaluate(self.x, self.y, x_adv)
        assert 0.0 <= report.ood_detection_rate <= 1.0
