import numpy as np
import pytest
from ai_core.learning_engine import LearningEngine, GradientLearner, EpisodicMemory, AdaptationEngine


def test_gradient_learner_forward():
    learner = GradientLearner(input_dim=8, output_dim=4)
    x = np.random.randn(8)
    out = learner.forward(x)
    assert out.shape == (4,)
    assert np.all(np.abs(out) <= 1.0 + 1e-6)


def test_gradient_learner_train_step():
    learner = GradientLearner(input_dim=8, output_dim=4)
    x = np.random.randn(8)
    target = np.random.randn(4)
    loss = learner.train_step(x, target)
    assert loss >= 0.0
    assert len(learner.get_loss_history()) == 1


def test_episodic_memory_store_and_sample():
    mem = EpisodicMemory(capacity=100)
    for i in range(10):
        mem.store({"state": np.zeros(4), "action": i, "reward": float(i)})
    batch = mem.sample(5)
    assert len(batch) == 5


def test_adaptation_engine_momentum():
    adapter = AdaptationEngine(adaptation_rate=0.01, momentum=0.9)
    g1 = np.ones(4)
    g2 = np.ones(4)
    v1 = adapter.adapt(g1)
    v2 = adapter.adapt(g2)
    assert np.allclose(v2, 0.9 * v1 - 0.01 * g2)


def test_learning_engine_observe_and_learn():
    engine = LearningEngine(input_dim=4, output_dim=2)
    for _ in range(20):
        engine.observe(np.random.randn(4), 0, 1.0, np.random.randn(4), False)
    loss = engine.learn(batch_size=10)
    assert loss >= 0.0
    metrics = engine.get_metrics()
    assert "avg_loss" in metrics
