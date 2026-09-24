import numpy as np
import pytest
from adaptive_learning.lifelong_learning import LifelongLearning, TaskBatch


class TestLifelongLearning:
    def test_initialization(self):
        ll = LifelongLearning(ewc_lambda=100.0, buffer_size=50)
        assert ll.ewc_lambda == 100.0
        assert ll.buffer_size == 50
        assert len(ll.progressive_columns) == 0

    def test_learn_task(self):
        ll = LifelongLearning()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        result = ll.learn_task("task1", task)
        assert result["task_id"] == "task1"
        assert "loss" in result
        assert "task1" in ll.seen_tasks

    def test_learn_multiple_tasks(self):
        ll = LifelongLearning()
        for i in range(3):
            task = TaskBatch(
                support_x=np.random.randn(10, 4),
                support_y=np.random.randint(0, 2, size=10),
                query_x=np.random.randn(5, 4),
                query_y=np.random.randint(0, 2, size=5),
            )
            ll.learn_task(f"task{i}", task)
        assert len(ll.seen_tasks) == 3
        assert len(ll.progressive_columns) == 3

    def test_progressive_columns(self):
        ll = LifelongLearning()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        ll.learn_task("task1", task)
        assert "task1_W" in ll.progressive_columns["task1"] or any("task1" in k for k in ll.progressive_columns["task1"].keys())

    def test_get_lifelong_report(self):
        ll = LifelongLearning()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        ll.learn_task("task1", task)
        report = ll.get_lifelong_report()
        assert report["num_tasks"] == 1
        assert report["columns"] >= 1
