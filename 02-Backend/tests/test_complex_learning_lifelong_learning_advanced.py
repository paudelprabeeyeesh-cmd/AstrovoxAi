import numpy as np
import pytest
from complex_learning.lifelong_learning_advanced import AdvancedLifelongLearner, TaskBatch


class TestAdvancedLifelongLearner:
    def test_initialization(self):
        all = AdvancedLifelongLearner(input_dim=16, hidden_dim=32, num_classes=5)
        assert all.input_dim == 16
        assert all.ewc_lambda == 100.0
        assert len(all.replay_buffer) == 0

    def test_learn_task(self):
        all = AdvancedLifelongLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        result = all.learn_task(task, use_replay=False, use_ewc=False, use_gem=False)
        assert result["task_id"] == "task"
        assert "loss" in result

    def test_learn_multiple_tasks(self):
        all = AdvancedLifelongLearner(input_dim=16)
        for i in range(3):
            task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                             query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
            all.learn_task(task, use_replay=False, use_ewc=False, use_gem=False)
        assert len(all.seen_tasks) == 3
        assert len(all.task_columns) == 3

    def test_evaluate_task(self):
        all = AdvancedLifelongLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        all.learn_task(task, use_replay=False, use_ewc=False, use_gem=False)
        result = all.evaluate_task(task)
        assert "loss" in result
        assert "accuracy" in result

    def test_replay_buffer_limit(self):
        all = AdvancedLifelongLearner(input_dim=16, buffer_size=5)
        for i in range(10):
            task = TaskBatch(support_x=np.random.randn(4, 16), support_y=np.random.randint(0, 3, size=4),
                             query_x=np.random.randn(2, 16), query_y=np.random.randint(0, 3, size=2))
            all.learn_task(task, use_replay=False, use_ewc=False, use_gem=False)
        assert len(all.replay_buffer) == 5

    def test_lifelong_report(self):
        all = AdvancedLifelongLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        all.learn_task(task, use_replay=False, use_ewc=False, use_gem=False)
        report = all.get_lifelong_report()
        assert "num_tasks" in report
        assert "columns" in report
