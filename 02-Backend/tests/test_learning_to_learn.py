import numpy as np
import pytest
from adaptive_learning.learning_to_learn import MetaLearner, TaskBatch


class TestMetaLearner:
    def test_initialization(self):
        meta = MetaLearner(inner_lr=0.01, outer_lr=0.001, adaptation_steps=5)
        assert meta.inner_lr == 0.01
        assert meta.outer_lr == 0.001
        assert meta.adaptation_steps == 5

    def test_initialize_params(self):
        meta = MetaLearner()
        meta.initialize_params({"W": (4, 3), "b": (3,)})
        assert "W" in meta.meta_params
        assert "b" in meta.meta_params
        assert meta.meta_params["W"].shape == (4, 3)

    def test_adapt_to_task(self):
        meta = MetaLearner()
        meta.initialize_params({"W": (4, 3), "b": (3,)})
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 3, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 3, size=5),
        )
        adapted = meta.adapt_to_task(task)
        assert "W" in adapted
        assert "b" in adapted

    def test_meta_train_step(self):
        meta = MetaLearner()
        meta.initialize_params({"W": (4, 3), "b": (3,)})
        tasks = []
        for _ in range(3):
            task = TaskBatch(
                support_x=np.random.randn(10, 4),
                support_y=np.random.randint(0, 3, size=10),
                query_x=np.random.randn(5, 4),
                query_y=np.random.randint(0, 3, size=5),
            )
            tasks.append(task)
        avg_loss = meta.meta_train_step(tasks)
        assert avg_loss > 0
        assert len(meta.task_history) == 3

    def test_softmax_stability(self):
        meta = MetaLearner()
        logits = np.array([[1000.0, 1001.0, 1002.0]])
        probs = meta._softmax(logits)
        assert np.allclose(np.sum(probs, axis=1), 1.0)
        assert not np.any(np.isnan(probs))

    def test_get_meta_params(self):
        meta = MetaLearner()
        meta.initialize_params({"W": (2, 2)})
        params = meta.get_meta_params()
        assert np.allclose(params["W"], meta.meta_params["W"])
