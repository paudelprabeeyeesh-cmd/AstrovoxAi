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
