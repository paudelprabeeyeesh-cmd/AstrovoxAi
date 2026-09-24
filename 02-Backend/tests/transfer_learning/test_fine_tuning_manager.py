import math

import pytest

from transfer_learning.fine_tuning_manager import FineTuneResult, FineTuneTask, FineTuningManager


class DummyModel:
    def __call__(self, x):
        return x


class TestFineTuneTask:
    def test_task_creation(self):
        task = FineTuneTask(task_id="t1", epochs=3, learning_rate=0.01)
        assert task.task_id == "t1"
        assert task.epochs == 3
        assert task.learning_rate == 0.01


class TestFineTuningManager:
    def test_manager_initialization(self):
        manager = FineTuningManager(model=DummyModel())
        assert manager.task_registry == {}
        assert manager.results == {}

    def test_register_task(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=2, learning_rate=0.01)
        assert "t1" in manager.task_registry

    def test_register_duplicate_task(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=2)
        with pytest.raises(ValueError):
            manager.register_task("t1", epochs=2)

    def test_run(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        result = manager.run("t1", [([1.0, 2.0], 1.0)])
        assert isinstance(result, FineTuneResult)
        assert result.task_id == "t1"

    def test_run_missing_task(self):
        manager = FineTuningManager(model=DummyModel())
        with pytest.raises(KeyError):
            manager.run("t1", [])

    def test_run_all(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        results = manager.run_all({"t1": [([1.0], 1.0)]})
        assert "t1" in results

    def test_get_history(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        manager.run("t1", [([1.0], 1.0)])
        history = manager.get_history("t1")
        assert isinstance(history, list)

    def test_get_history_missing(self):
        manager = FineTuningManager(model=DummyModel())
        with pytest.raises(KeyError):
            manager.get_history("t1")

    def test_summary(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        manager.run("t1", [([1.0], 1.0)])
        summary = manager.summary()
        assert "t1" in summary["registered_tasks"]
        assert "t1" in summary["completed_tasks"]

    def test_fine_tune_result_creation(self):
        result = FineTuneResult(task_id="t1", final_loss=0.5, steps=10)
        assert result.task_id == "t1"
        assert result.final_loss == 0.5
        assert result.steps == 10
        assert result.metrics == {}

    def test_default_loss_list_match(self):
        manager = FineTuningManager(model=DummyModel())
        loss = manager._default_loss([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        assert loss == 0.0

    def test_default_loss_list_mismatch(self):
        manager = FineTuningManager(model=DummyModel())
        loss = manager._default_loss([1.0, 2.0], [3.0, 4.0])
        assert loss == 1.0

    def test_default_loss_numbers(self):
        manager = FineTuningManager(model=DummyModel())
        loss = manager._default_loss(0.5, 1.0)
        assert math.isfinite(loss)
        assert loss == 0.5

    def test_apply_learning_rate(self):
        manager = FineTuningManager(model=DummyModel())
        lr = manager._apply_learning_rate(base_lr=0.1, epoch=0, total_epochs=10)
        assert math.isclose(lr, 0.1)
        lr = manager._apply_learning_rate(base_lr=0.1, epoch=5, total_epochs=10)
        assert math.isclose(lr, 0.05)

    def test_run_with_on_step(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=2)
        steps = []
        def on_step(step, loss):
            steps.append((step, loss))
        result = manager.run("t1", [([1.0], 1.0)], on_step=on_step)
        assert len(steps) == 2
        assert result.steps == 2

    def test_run_empty_data(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        result = manager.run("t1", [])
        assert result.steps == 0
        assert result.final_loss == 0.0

    def test_run_all_empty(self):
        manager = FineTuningManager(model=DummyModel())
        results = manager.run_all({})
        assert results == {}

    def test_get_history_after_run_all(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=1)
        manager.run_all({"t1": [([1.0], 1.0)]})
        history = manager.get_history("t1")
        assert isinstance(history, list)
        assert len(history) == 1

    def test_summary_empty(self):
        manager = FineTuningManager(model=DummyModel())
        summary = manager.summary()
        assert summary["registered_tasks"] == []
        assert summary["completed_tasks"] == []
        assert summary["task_losses"] == {}

    def test_register_task_with_metadata(self):
        manager = FineTuningManager(model=DummyModel())
        manager.register_task("t1", epochs=3, learning_rate=0.05, dataset="mnist")
        task = manager.task_registry["t1"]
        assert task.metadata == {"dataset": "mnist"}
