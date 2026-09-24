
from complex_learning.continual_learning_advanced import AdvancedContinualLearner, TaskBatch
import numpy as np


class TestAdvancedContinualLearner:
    def test_initialization(self):
        cl = AdvancedContinualLearner(input_dim=8)
        assert cl.input_dim == 8
        assert cl.hidden_dim == 64
        assert cl.num_classes == 5
        assert len(cl.params) == 4

    def test_forward(self):
        cl = AdvancedContinualLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        h, logits = cl._forward(x)
        assert h.shape == (4, 64)
        assert logits.shape == (4, 5)

    def test_compute_loss(self):
        cl = AdvancedContinualLearner(input_dim=8)
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = cl._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_learn_task(self):
        cl = AdvancedContinualLearner(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        cl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        task = TaskBatch(
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            task_id="task_0",
        )
        result = cl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        assert result["task_id"] == "task_0"
        assert "loss" in result
        assert "buffer_size" in result
        assert len(cl.seen_tasks) == 1

    def test_evaluate_task(self):
        cl = AdvancedContinualLearner(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        cl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        task = TaskBatch(
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            np.random.randn(4, 8).astype(np.float64),
            np.array([0, 1, 2, 0]),
            task_id="task_0",
        )
        result = cl.evaluate_task(task)
        assert "loss" in result
        assert "accuracy" in result
        assert "predictions" in result

    def test_forget_free_metric(self):
        cl = AdvancedContinualLearner(input_dim=8)
        cl.loss_history = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
        metric = cl.forget_free_metric()
        assert isinstance(metric, float)
        assert metric >= 0.0

    def test_get_continual_report(self):
        cl = AdvancedContinualLearner(input_dim=8)
        report = cl.get_continual_report()
        assert "num_tasks" in report
        assert "buffer_size" in report
        assert "forget_free_metric" in report

    def test_multiple_tasks(self):
        cl = AdvancedContinualLearner(input_dim=8, hidden_dim=16, num_classes=3, buffer_size=20)
        np.random.seed(42)
        cl.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        for tid in range(3):
            task = TaskBatch(
                np.random.randn(4, 8).astype(np.float64),
                np.array([tid % 3, (tid + 1) % 3, tid % 3, (tid + 1) % 3]),
                np.random.randn(4, 8).astype(np.float64),
                np.array([tid % 3, (tid + 1) % 3, tid % 3, (tid + 1) % 3]),
                task_id=f"task_{tid}",
            )
            cl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        assert len(cl.seen_tasks) == 3
        report = cl.get_continual_report()
        assert report["num_tasks"] == 3
