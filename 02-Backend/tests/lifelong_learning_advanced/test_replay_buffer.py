import numpy as np

from lifelong_learning_advanced.replay_buffer import ReplayBuffer, ReplaySample


class TestReplayBuffer:
    def test_add_sample(self):
        buf = ReplayBuffer(capacity=10)
        x = np.array([1.0, 2.0])
        y = np.array([0.0])
        buf.add(x, y, task_id="t1")
        assert len(buf) == 1

    def test_add_batch(self):
        buf = ReplayBuffer(capacity=100)
        x = np.random.randn(5, 3)
        y = np.random.randn(5, 2)
        buf.add_batch(x, y, task_id="t1")
        assert len(buf) == 5

    def test_sample(self):
        buf = ReplayBuffer(capacity=100)
        x = np.random.randn(10, 3)
        y = np.random.randn(10, 2)
        buf.add_batch(x, y, task_id="t1")
        xb, yb = buf.sample(4)
        assert xb.shape == (4, 3)
        assert yb.shape == (4, 2)

    def test_sample_overflow(self):
        buf = ReplayBuffer(capacity=3)
        buf.add(np.array([1.0]), np.array([0.0]), task_id="t1")
        buf.add(np.array([2.0]), np.array([1.0]), task_id="t1")
        buf.add(np.array([3.0]), np.array([2.0]), task_id="t1")
        buf.add(np.array([4.0]), np.array([3.0]), task_id="t1")
        assert len(buf) == 3

    def test_sample_empty(self):
        buf = ReplayBuffer()
        try:
            buf.sample(1)
        except ValueError:
            assert True
        else:
            assert False

    def test_sample_task(self):
        buf = ReplayBuffer(capacity=100)
        buf.add(np.array([1.0]), np.array([0.0]), task_id="t1")
        buf.add(np.array([2.0]), np.array([1.0]), task_id="t2")
        xb, yb = buf.sample_task("t1", 1)
        assert xb.shape == (1, 1)

    def test_sample_task_missing(self):
        buf = ReplayBuffer()
        try:
            buf.sample_task("missing", 1)
        except ValueError:
            assert True
        else:
            assert False

    def test_clear(self):
        buf = ReplayBuffer()
        buf.add(np.array([1.0]), np.array([0.0]))
        buf.clear()
        assert len(buf) == 0

    def test_stats(self):
        buf = ReplayBuffer(capacity=10)
        buf.add(np.array([1.0]), np.array([0.0]), task_id="t1")
        buf.add(np.array([2.0]), np.array([1.0]), task_id="t1")
        buf.add(np.array([3.0]), np.array([2.0]), task_id="t2")
        stats = buf.stats()
        assert stats["total"] == 3
        assert stats["capacity"] == 10
        assert stats["tasks"]["t1"] == 2
        assert stats["tasks"]["t2"] == 1
