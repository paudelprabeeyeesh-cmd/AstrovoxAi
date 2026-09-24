import math
from advanced_security.adversarial_defense import (
    AdversarialDefense,
    AdversarialTrainer,
    LabelSmoothing,
    RandomizedSmoothing,
)


def test_adversarial_trainer_fgsm() -> None:
    trainer = AdversarialTrainer()
    weights = [1.0, 2.0, 3.0]
    grad = [1.0, 0.0, -1.0]
    result = trainer.fgsm(weights, grad)
    assert len(result) == len(weights)


def test_adversarial_trainer_pgd() -> None:
    trainer = AdversarialTrainer(iterations=5)
    weights = [1.0, 2.0, 3.0]
    grad = [1.0, 0.0, -1.0]
    result = trainer.pgd(weights, grad)
    assert len(result) == len(weights)


def test_adversarial_defense_gaussian_noise() -> None:
    defense = AdversarialDefense()
    data = [1.0, 2.0, 3.0]
    noised = defense.gaussian_noise(data)
    assert len(noised) == len(data)


def test_adversarial_defense_gradient_pruning() -> None:
    defense = AdversarialDefense()
    grads = [0.1, 0.5, 0.9, 1.5, 2.5]
    pruned = defense.gradient_pruning(grads, 0.8)
    assert pruned[0] == 0.0
    assert pruned[1] == 0.0
    assert pruned[2] == 0.9


def test_adversarial_defense_outlier_detection() -> None:
    defense = AdversarialDefense()
    data = [1.0, 2.0, 3.0, 4.0, 100.0]
    outliers = defense.detect_outlier(data, std_threshold=1.5)
    assert 4 in outliers


def test_randomized_smoothing() -> None:
    rs = RandomizedSmoothing(sigma=0.1, num_samples=4)
    weights = [1.0, 2.0, 3.0]
    result = rs.smooth(weights)
    assert len(result) == len(weights)


def test_label_smoothing() -> None:
    ls = LabelSmoothing(smoothing=0.1)
    probs = [0.8, 0.2]
    result = ls.apply(probs)
    assert abs(sum(result) - 1.0) < 1e-6
    assert abs(result[0] - 0.77) < 1e-6
