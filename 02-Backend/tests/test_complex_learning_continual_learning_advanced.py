import numpy as np
import pytest
from complex_learning.continual_learning_advanced import AdvancedContinualLearner, TaskBatch


class TestAdvancedContinualLearner:
    def test_initialization(self):
        acl = AdvancedContinualLearner(input_dim=16)
        assert acl.input_dim == 16
        assert len(acl.replay_buffer) == 0
        assert len(acl.seen_tasks) == 0

    def test_learn_task(self):
        acl = AdvancedContinualLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        result = acl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        assert result["task_id"] == "task"
        assert "loss" in result

    def test_multiple_tasks(self):
        acl = AdvancedContinualLearner(input_dim=16)
        for i in range(3):
            task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                             query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
            acl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        assert len(acl.seen_tasks) == 3
        assert len(acl.replay_buffer) == 3

    def test_evaluate_task(self):
        acl = AdvancedContinualLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        acl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        result = acl.evaluate_task(task)
        assert "loss" in result
        assert "accuracy" in result

    def test_replay_buffer_limit(self):
        acl = AdvancedContinualLearner(input_dim=16, buffer_size=5)
        for i in range(10):
            task = TaskBatch(support_x=np.random.randn(4, 16), support_y=np.random.randint(0, 3, size=4),
                             query_x=np.random.randn(2, 16), query_y=np.random.randint(0, 3, size=2))
            acl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        assert len(acl.replay_buffer) == 5

    def test_continual_report(self):
        acl = AdvancedContinualLearner(input_dim=16)
        task = TaskBatch(support_x=np.random.randn(8, 16), support_y=np.random.randint(0, 3, size=8),
                         query_x=np.random.randn(4, 16), query_y=np.random.randint(0, 3, size=4))
        acl.learn_task(task, use_replay=False, use_ewc=False, use_lwf=False)
        report = acl.get_continual_report()
        assert "num_tasks" in report
        assert "forget_free_metric" in report
