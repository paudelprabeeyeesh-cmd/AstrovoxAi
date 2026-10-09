
from complex_learning.lifelong_learning_advanced import AdvancedLifelongLearner, TaskBatch
import numpy as np


class TestAdvancedLifelongLearner:
    def test_initialization(self):
        ll = AdvancedLifelongLearner(input_dim=8)
        assert ll.input_dim == 8
        assert ll.hidden_dim == 64
        assert ll.num_classes == 5
        assert len(ll.params) == 4

    def test_forward(self):
        ll = AdvancedLifelongLearner(input_dim=8)
        x = np.random.randn(4, 8).astype(np.float64)
        h, logits = ll._forward(x)
        assert h.shape == (4, 64)
        assert logits.shape == (4, 5)

    def test_compute_loss(self):
        ll = AdvancedLifelongLearner(input_dim=8)
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = ll._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_learn_task(self):
        ll = AdvancedLifelongLearner(input_dim=8, hidden_dim=16, num_classes=3, buffer_size=20)
        np.random.seed(42)
        ll.params = {
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
        result = ll.learn_task(task, use_replay=False, use_ewc=False)
        assert result["task_id"] == "task_0"
        assert "loss" in result
        assert len(ll.seen_tasks) == 1

    def test_gem_correction(self):
        ll = AdvancedLifelongLearner(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        ll.params = {
            "W1": np.random.randn(8, 16).astype(np.float64) * 0.1,
            "b1": np.zeros(16, dtype=np.float64),
            "W2": np.random.randn(16, 3).astype(np.float64) * 0.1,
            "b2": np.zeros(3, dtype=np.float64),
        }
        h = np.maximum(np.random.randn(4, 8) @ ll.params["W1"] + ll.params["b1"], 0)
        logits = h @ ll.params["W2"] + ll.params["b2"]
        probs = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs /= np.sum(probs, axis=1, keepdims=True)
        y = np.array([0, 1, 2, 0])
        grad = probs.copy()
        grad[np.arange(len(y)), y] -= 1
        grad /= len(y)
        dW2 = h.T @ grad
        grads = {"W1": np.zeros_like(ll.params["W1"]), "b1": np.zeros_like(ll.params["b1"]),
                 "W2": dW2, "b2": np.sum(grad, axis=0)}
        ll.gradient_history.append(grads)
        grads["W1"] = np.random.randn(*ll.params["W1"].shape).astype(np.float64)
        corrected = ll._gem_correction(grads)
        assert corrected["W2"].shape == ll.params["W2"].shape

    def test_evaluate_task(self):
        ll = AdvancedLifelongLearner(input_dim=8, hidden_dim=16, num_classes=3)
        np.random.seed(42)
        ll.params = {
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
        result = ll.evaluate_task(task)
        assert "loss" in result
        assert "accuracy" in result
        assert "predictions" in result

    def test_multiple_tasks(self):
        ll = AdvancedLifelongLearner(input_dim=8, hidden_dim=16, num_classes=3, buffer_size=20)
        np.random.seed(42)
        ll.params = {
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
            ll.learn_task(task, use_replay=False, use_ewc=False)
        assert len(ll.seen_tasks) == 3

    def test_get_lifelong_report(self):
        ll = AdvancedLifelongLearner(input_dim=8)
        report = ll.get_lifelong_report()
        assert "num_tasks" in report
        assert "buffer_size" in report
        assert "columns" in report
