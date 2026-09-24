
from complex_learning.multi_task_advanced import AdvancedMultiTaskModel
import numpy as np


class TestAdvancedMultiTaskModel:
    def test_initialization(self):
        mtl = AdvancedMultiTaskModel()
        assert mtl.shared_dim == 64
        assert mtl.task_hidden_dim == 64
        assert mtl.uncertainty_weighting is True

    def test_init_shared(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        assert "W1" in mtl.shared_params
        assert mtl.shared_params["W1"].shape == (8, 64)

    def test_add_task(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        assert "task_a" in mtl.task_params
        assert "task_a" in mtl.task_weights
        assert mtl.task_params["task_a"]["W"].shape == (64, 3)

    def test_forward_task(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        x = np.random.randn(4, 8).astype(np.float64)
        logits = mtl._forward_task(x, "task_a")
        assert logits.shape == (4, 3)

    def test_compute_loss(self):
        mtl = AdvancedMultiTaskModel()
        logits = np.random.randn(4, 5).astype(np.float64)
        y = np.array([0, 1, 2, 3])
        loss = mtl._compute_loss(logits, y)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_train_step(self):
        np.random.seed(42)
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        loss = mtl.train_step(x, y, "task_a", lr=0.01)
        assert isinstance(loss, float)
        assert len(mtl.task_losses["task_a"]) == 1

    def test_multi_task_train_step(self):
        np.random.seed(42)
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        batches = {
            "task_a": (np.random.randn(4, 8).astype(np.float64), np.array([0, 1, 2, 0])),
            "task_b": (np.random.randn(4, 8).astype(np.float64), np.array([0, 1, 2, 0])),
        }
        result = mtl.multi_task_train_step(batches, lr=0.01)
        assert "total_loss" in result
        assert "task_losses" in result
        assert "task_a" in result["task_losses"]
        assert "task_b" in result["task_losses"]

    def test_set_task_weights(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        mtl.set_task_weights({"task_a": 2.0})
        assert mtl.task_weights["task_a"] == 2.0

    def test_get_task_weights(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        weights = mtl.get_task_weights()
        assert "task_a" in weights
        assert weights["task_a"] == 1.0

    def test_get_multi_task_report(self):
        mtl = AdvancedMultiTaskModel()
        mtl.init_shared(input_dim=8)
        mtl.add_task("task_a", output_dim=3)
        x = np.random.randn(4, 8).astype(np.float64)
        y = np.array([0, 1, 2, 0])
        mtl.train_step(x, y, "task_a")
        report = mtl.get_multi_task_report()
        assert "num_tasks" in report
        assert "total_steps" in report
        assert "task_weights" in report
