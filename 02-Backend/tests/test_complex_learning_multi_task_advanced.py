import numpy as np
from complex_learning.multi_task_advanced import AdvancedMultiTaskModel


class TestAdvancedMultiTaskModel:
    def test_initialization(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        assert mtm.shared_dim == 64
        assert len(mtm.task_params) == 0

    def test_init_shared(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        assert "W1" in mtm.shared_params
        assert mtm.shared_params["W1"].shape == (8, 64)

    def test_add_task(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        assert "task1" in mtm.task_params
        assert mtm.task_params["task1"]["W"].shape == (64, 3)

    def test_set_task_weights(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        mtm.set_task_weights({"task1": 2.0})
        assert mtm.task_weights["task1"] == 2.0

    def test_train_step(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        x = np.random.randn(10, 8)
        y = np.random.randint(0, 3, size=10)
        loss = mtm.train_step(x, y, "task1", lr=0.01)
        assert isinstance(loss, float)
        assert loss >= 0.0

    def test_multi_task_train_step(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        mtm.add_task("task2", output_dim=2)
        batches = {
            "task1": (np.random.randn(10, 8), np.random.randint(0, 3, size=10)),
            "task2": (np.random.randn(10, 8), np.random.randint(0, 2, size=10)),
        }
        result = mtm.multi_task_train_step(batches, lr=0.01)
        assert "total_loss" in result
        assert "task_losses" in result
        assert len(result["task_losses"]) == 2

    def test_get_task_weights(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        weights = mtm.get_task_weights()
        assert "task1" in weights

    def test_multi_task_report(self):
        mtm = AdvancedMultiTaskModel(shared_dim=64)
        mtm.init_shared(input_dim=8)
        mtm.add_task("task1", output_dim=3)
        batches = {"task1": (np.random.randn(10, 8), np.random.randint(0, 3, size=10))}
        mtm.multi_task_train_step(batches, lr=0.01)
        report = mtm.get_multi_task_report()
        assert "num_tasks" in report
        assert "per_task_losses" in report
