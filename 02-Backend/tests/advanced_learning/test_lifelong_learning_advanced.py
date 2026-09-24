import numpy as np
import pytest
from advanced_learning.lifelong_learning_advanced import AdvancedLifelongLearner, LifelongConfig


class TestAdvancedLifelongLearner:
    def test_initialization(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        assert lll.config.input_dim == 32
        assert lll.config.output_dim == 4
        assert lll.task_count == 0
        assert len(lll.loss_history) == 0

    def test_learn_task(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        result = lll.learn_task(x, y, steps=5)
        assert "task_id" in result
        assert result["task_id"] == 1
        assert lll.task_count == 1
        assert len(lll.buffer) <= config.max_buffer_size

    def test_learn_multiple_tasks(self):
        config = LifelongConfig(input_dim=32, output_dim=4, num_tasks=3)
        lll = AdvancedLifelongLearner(config)
        for task_id in range(1, 4):
            x = np.random.randn(20, 32).astype(np.float64)
            y = np.random.randn(20, 4).astype(np.float64)
            lll.learn_task(x, y, steps=3)
        assert lll.task_count == 3

    def test_knowledge_distillation_step(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        x = np.random.randn(20, 32).astype(np.float64)
        old_logits = np.random.randn(20, 4).astype(np.float64)
        result = lll.knowledge_distillation_step(x, old_logits)
        assert "kd_loss" in result

    def test_replay_step(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        x = np.random.randn(10, 32).astype(np.float64)
        y = np.random.randn(10, 4).astype(np.float64)
        lll.learn_task(x, y, steps=2)
        result = lll.replay_step(batch_size=5)
        assert "replay_loss" in result

    def test_replay_step_empty(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        result = lll.replay_step()
        assert result["replay_loss"] is None

    def test_get_lifelong_report(self):
        config = LifelongConfig(input_dim=32, output_dim=4)
        lll = AdvancedLifelongLearner(config)
        x = np.random.randn(20, 32).astype(np.float64)
        y = np.random.randn(20, 4).astype(np.float64)
        lll.learn_task(x, y, steps=3)
        report = lll.get_lifelong_report()
        assert "tasks_learned" in report
        assert report["tasks_learned"] == 1
