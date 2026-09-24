import numpy as np
import pytest
from advanced_learning.continual_learning_advanced import AdvancedContinualLearner, ContinualConfig


class TestAdvancedContinualLearner:
    def test_initialization(self):
        config = ContinualConfig(input_dim=32, output_dim=4)
        cl = AdvancedContinualLearner(config)
        assert cl.config.input_dim == 32
        assert cl.config.num_tasks == 3
        assert cl.current_task == 0
        assert len(cl.loss_history) == 0

    def test_start_task(self):
        config = ContinualConfig(input_dim=32, output_dim=4, num_tasks=3)
        cl = AdvancedContinualLearner(config)
        cl.start_task(1)
        assert cl.current_task == 1
        assert len(cl.task_boundaries) == 1

    def test_train_step(self):
        config = ContinualConfig(input_dim=32, output_dim=4)
        cl = AdvancedContinualLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        result = cl.train_step(x, y)
        assert "loss" in result
        assert "task_id" in result
        assert len(cl.loss_history) == 1

    def test_train_step_with_replay(self):
        config = ContinualConfig(input_dim=32, output_dim=4, max_replay_size=100)
        cl = AdvancedContinualLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        cl.start_task(1)
        cl.train_step(x, y)
        x2 = np.random.randn(16, 32).astype(np.float64)
        y2 = np.random.randn(16, 4).astype(np.float64)
        result = cl.train_step(x2, y2)
        assert "loss" in result

    def test_evaluate_task(self):
        config = ContinualConfig(input_dim=32, output_dim=4)
        cl = AdvancedContinualLearner(config)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        result = cl.evaluate_task(x, y, task_id=1)
        assert "task_loss" in result
        assert result["task_id"] == 1

    def test_get_continual_report(self):
        config = ContinualConfig(input_dim=32, output_dim=4, num_tasks=3)
        cl = AdvancedContinualLearner(config)
        cl.start_task(1)
        x = np.random.randn(16, 32).astype(np.float64)
        y = np.random.randn(16, 4).astype(np.float64)
        cl.train_step(x, y)
        report = cl.get_continual_report()
        assert "current_task" in report
        assert report["tasks_encountered"] == 1
        assert "replay_buffer_size" in report

    def test_replay_buffer_grows(self):
        config = ContinualConfig(input_dim=32, output_dim=4, max_replay_size=200)
        cl = AdvancedContinualLearner(config)
        cl.start_task(1)
        x = np.random.randn(50, 32).astype(np.float64)
        y = np.random.randn(50, 4).astype(np.float64)
        cl.train_step(x, y)
        assert len(cl.replay_buffer) == 50
