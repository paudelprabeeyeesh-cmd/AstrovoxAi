import math
import random
from online_learning.sample_selector import SampleSelector


class TestSampleSelector:
    def test_initialization(self):
        selector = SampleSelector(strategy="random", buffer_size=100)
        assert selector.strategy == "random"
        assert selector.buffer_size == 100
        assert len(selector.buffer) == 0

    def test_add_sample(self):
        selector = SampleSelector()
        selector.add([1.0, 2.0], 3.0, loss=0.5)
        assert len(selector.buffer) == 1
        assert len(selector.losses) == 1

    def test_select_random(self):
        selector = SampleSelector(strategy="random")
        for i in range(20):
            selector.add([float(i)], float(i))
        selected = selector.select(5)
        assert len(selected) == 5

    def test_select_loss(self):
        selector = SampleSelector(strategy="loss")
        for i in range(10):
            selector.add([float(i)], float(i), loss=float(i))
        selected = selector.select(3)
        assert len(selected) == 3
        assert all(s[1] >= 7.0 for s in selected)

    def test_buffer_overflow(self):
        selector = SampleSelector(buffer_size=5)
        for i in range(10):
            selector.add([float(i)], float(i))
        assert len(selector.buffer) <= 5

    def test_get_stats(self):
        selector = SampleSelector()
        selector.add([1.0], 1.0, loss=0.1)
        selector.add([2.0], 2.0, loss=0.2)
        stats = selector.get_stats()
        assert stats["buffer_size"] == 2
        assert stats["strategy"] == "random"
        assert math.isclose(stats["mean_loss"], 0.15)
