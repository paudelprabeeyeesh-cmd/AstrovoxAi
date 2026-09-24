import numpy as np
import pytest
from emergent_abilities.few_shot_learning import FewShotLearner, FewShotAdaptationCurve


class TestFewShotLearner:
    def test_add_support(self):
        learner = FewShotLearner(embedding_dim=16, num_classes=3)
        emb = np.random.randn(16)
        learner.add_support(emb, label=0)
        assert len(learner.support_examples[0]) == 1

    def test_build_prototypes(self):
        learner = FewShotLearner(embedding_dim=16, num_classes=2)
        for label in [0, 1]:
            for _ in range(5):
                learner.add_support(np.random.randn(16), label=label)
        learner.build_prototypes()
        assert 0 in learner.class_prototypes
        assert 1 in learner.class_prototypes
        assert learner.class_prototypes[0].shape == (16,)

    def test_classify_with_prototypes(self):
        learner = FewShotLearner(embedding_dim=16, num_classes=2)
        for label in [0, 1]:
            for _ in range(5):
                learner.add_support(np.random.randn(16) + label * 0.5, label=label)
        learner.build_prototypes()
        query = np.random.randn(16)
        pred, conf = learner.classify(query)
        assert pred in [0, 1]
        assert 0.0 <= conf <= 1.0

    def test_classify_empty_prototypes(self):
        learner = FewShotLearner(embedding_dim=16, num_classes=2)
        query = np.random.randn(16)
        pred, conf = learner.classify(query)
        assert pred == 0
        assert conf == 0.0

    def test_adaptation_curve(self):
        learner = FewShotLearner(embedding_dim=16, num_classes=2)
        for label in [0, 1]:
            for _ in range(10):
                learner.add_support(np.random.randn(16) + label * 0.5, label=label)
        query_embs = np.random.randn(5, 16)
        query_labels = np.array([0, 0, 1, 1, 0])
        curve = learner.adaptation_curve(query_embs, query_labels)
        assert len(curve) == 20
        assert all(0.0 <= r.accuracy <= 1.0 for r in curve)


class TestFewShotAdaptationCurve:
    def test_record_performance(self):
        curve = FewShotAdaptationCurve(max_shots=20)
        curve.record("task_a", num_shots=5, accuracy=0.8)
        assert len(curve.curves["task_a"]) == 5
        assert curve.curves["task_a"][4] == 0.8

    def test_fit_power_law(self):
        curve = FewShotAdaptationCurve(max_shots=10)
        for shots in range(1, 11):
            acc = 0.5 + 0.4 * (1 - np.exp(-shots / 3.0))
            curve.record("task_a", shots, acc)
        result = curve.fit_power_law("task_a")
        assert result is not None
        intercept, exponent = result
        assert exponent != 0.0

    def test_sample_efficiency_metric(self):
        curve = FewShotAdaptationCurve(max_shots=20)
        for shots in range(1, 21):
            curve.record("task_a", shots, min(1.0, shots * 0.05))
        metric = curve.sample_efficiency_metric("task_a", target_accuracy=0.5)
        assert metric == 10.0

    def test_sample_efficiency_not_reached(self):
        curve = FewShotAdaptationCurve(max_shots=5)
        curve.record("task_a", 1, 0.1)
        metric = curve.sample_efficiency_metric("task_a", target_accuracy=0.9)
        assert metric == float('inf')
