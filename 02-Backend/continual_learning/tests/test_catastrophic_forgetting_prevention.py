import numpy as np
import pytest
from ..catastrophic_forgetting_prevention import (
    EWCMemory,
    ReplayBuffer,
    CatastrophicForgettingPrevention
)


class TestEWCMemory:
    def test_initialization(self):
        ewc = EWCMemory(ewc_lambda=100.0)
        assert ewc.ewc_lambda == 100.0
        assert ewc.task_count == 0

    def test_update_with_gradients(self):
        ewc = EWCMemory()
        state = {"layer1": np.array([1.0, 2.0, 3.0]), "layer2": np.array([4.0, 5.0])}
        gradients = {"layer1": np.array([0.1, 0.2, 0.3]), "layer2": np.array([0.4, 0.5])}

        result = ewc.update(state, "task1", gradients=gradients)

        assert ewc.task_count == 1
        assert np.array_equal(ewc.optimal_params["layer1"], np.array([1.0, 2.0, 3.0]))
        assert np.allclose(ewc.fisher_information["layer1"], np.array([0.01, 0.04, 0.09]))

    def test_update_without_gradients(self):
        ewc = EWCMemory()
        state = {"layer1": np.array([1.0, 2.0])}
        ewc.update(state, "task1")
        assert ewc.task_count == 1

    def test_ewc_loss_zero_when_optimal(self):
        ewc = EWCMemory(ewc_lambda=100.0)
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        ewc.update(state, "task1")

        loss = ewc.compute_ewc_loss(state)
        assert np.isclose(loss, 0.0)

    def test_ewc_loss_nonzero_when_changed(self):
        ewc = EWCMemory(ewc_lambda=100.0)
        state = {"layer1": np.array([1.0, 2.0, 3.0])}
        ewc.update(state, "task1")

        new_state = {"layer1": np.array([2.0, 3.0, 4.0])}
        loss = ewc.compute_ewc_loss(new_state)
        assert loss > 0

    def test_ewc_loss_penalizes_important_weights_more(self):
        ewc = EWCMemory(ewc_lambda=1.0)
        state = {"layer1": np.array([1.0, 2.0])}
        gradients = {"layer1": np.array([10.0, 0.1])}
        ewc.update(state, "task1", gradients=gradients)

        new_state = {"layer1": np.array([1.5, 1.5])}
        loss = ewc.compute_ewc_loss(new_state)

        diff = np.abs(new_state["layer1"] - state["layer1"])
        expected_loss = 0.5 * 1.0 * np.sum(gradients["layer1"] ** 2 * diff ** 2)
        assert np.isclose(loss, expected_loss)

    def test_get_importance(self):
        ewc = EWCMemory()
        gradients = {"layer1": np.array([0.1, 0.2, 0.3])}
        ewc.update({"layer1": np.array([1.0, 2.0, 3.0])}, "task1", gradients=gradients)

        importance = ewc.get_importance("layer1")
        assert np.allclose(importance, np.array([0.01, 0.04, 0.09]))

    def test_get_importance_unknown_layer(self):
        ewc = EWCMemory()
        importance = ewc.get_importance("unknown_layer")
        assert importance.size == 1
        assert importance[0] == 0.0


class TestReplayBuffer:
    def test_initialization(self):
        rb = ReplayBuffer(buffer_size=1000)
        assert rb.buffer_size == 1000
        assert len(rb.buffer) == 0

    def test_store_sample(self):
        rb = ReplayBuffer(buffer_size=1000)
        sample = {"layer1": np.array([1.0, 2.0])}
        rb.store_sample("task1", sample)

        assert len(rb.buffer) == 1
        assert len(rb.task_data["task1"]) == 1

    def test_buffer_overflow(self):
        rb = ReplayBuffer(buffer_size=2)
        sample1 = {"layer1": np.array([1.0])}
        sample2 = {"layer1": np.array([2.0])}
        sample3 = {"layer1": np.array([3.0])}

        rb.store_sample("task1", sample1)
        rb.store_sample("task1", sample2)
        rb.store_sample("task1", sample3)

        assert len(rb.buffer) == 2
        assert rb.buffer[0][1]["layer1"][0] == 2.0
        assert rb.buffer[1][1]["layer1"][0] == 3.0

    def test_sample_batch(self):
        rb = ReplayBuffer(buffer_size=1000)
        for i in range(100):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task1", sample)

        batch = rb.sample_batch(10, task_id="task1")
        assert len(batch) == 10

    def test_sample_batch_empty(self):
        rb = ReplayBuffer(buffer_size=1000)
        batch = rb.sample_batch(10)
        assert len(batch) == 0

    def test_sample_batch_wrong_task(self):
        rb = ReplayBuffer(buffer_size=1000)
        for i in range(10):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task1", sample)

        batch = rb.sample_batch(5, task_id="task2")
        assert len(batch) == 0

    def test_get_buffer_stats(self):
        rb = ReplayBuffer(buffer_size=1000)
        for i in range(100):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task1", sample)
        for i in range(50):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task2", sample)

        stats = rb.get_buffer_stats()
        assert stats["total_samples"] == 150
        assert stats["utilization"] == 0.15
        assert len(stats["tasks"]) == 2
        assert stats["samples_per_task"]["task1"] == 100
        assert stats["samples_per_task"]["task2"] == 50

    def test_get_importance(self):
        rb = ReplayBuffer(buffer_size=1000)
        for i in range(10):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task1", sample)
        for i in range(5):
            sample = {"layer1": np.array([float(i)])}
            rb.store_sample("task2", sample)

        importance = rb.get_importance("layer1")
        assert np.isclose(importance[0], 1.0)
