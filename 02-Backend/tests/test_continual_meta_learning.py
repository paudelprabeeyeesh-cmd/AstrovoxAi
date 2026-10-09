import numpy as np
from adaptive_learning.continual_meta_learning import ContinualMetaLearner, TaskBatch


class TestContinualMetaLearner:
    def test_initialization(self):
        cml = ContinualMetaLearner(buffer_size=50)
        assert cml.buffer_size == 50
        assert len(cml.replay_buffer) == 0

    def test_learn_task(self):
        cml = ContinualMetaLearner()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        result = cml.learn_task("task1", task)
        assert result["task_id"] == "task1"
        assert "loss" in result
        assert "task1" in cml.seen_tasks

    def test_learn_multiple_tasks(self):
        cml = ContinualMetaLearner()
        for i in range(3):
            task = TaskBatch(
                support_x=np.random.randn(10, 4),
                support_y=np.random.randint(0, 2, size=10),
                query_x=np.random.randn(5, 4),
                query_y=np.random.randint(0, 2, size=5),
            )
            cml.learn_task(f"task{i}", task)
        assert len(cml.seen_tasks) == 3
        assert len(cml.task_performance) == 3

    def test_replay_buffer(self):
        cml = ContinualMetaLearner(buffer_size=10)
        for i in range(15):
            task = TaskBatch(
                support_x=np.random.randn(10, 4),
                support_y=np.random.randint(0, 2, size=10),
                query_x=np.random.randn(5, 4),
                query_y=np.random.randint(0, 2, size=5),
            )
            cml.learn_task(f"task{i}", task, use_replay=False)
        assert len(cml.replay_buffer) == 10

    def test_evaluate_task(self):
        cml = ContinualMetaLearner()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        cml.learn_task("task1", task)
        loss = cml.evaluate_task(task)
        assert isinstance(loss, float)

    def test_task_statistics(self):
        cml = ContinualMetaLearner()
        task = TaskBatch(
            support_x=np.random.randn(10, 4),
            support_y=np.random.randint(0, 2, size=10),
            query_x=np.random.randn(5, 4),
            query_y=np.random.randint(0, 2, size=5),
        )
        for _ in range(5):
            cml.learn_task("task1", task)
        stats = cml.get_task_statistics()
        assert "task1" in stats
        assert "mean_loss" in stats["task1"]
