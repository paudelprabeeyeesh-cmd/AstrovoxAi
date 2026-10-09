import json
import os

from training_engine.checkpoint_manager import CheckpointManager


def test_save_and_load(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    path = manager.save(step=1, state={"weights": [1.0, 2.0], "lr": 0.01})
    assert os.path.exists(path)
    loaded_step, loaded_state = manager.load(1)
    assert loaded_step == 1
    assert loaded_state["weights"] == [1.0, 2.0]
    assert loaded_state["lr"] == 0.01


def test_latest_returns_max_step(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    manager.save(step=3, state={})
    manager.save(step=1, state={})
    assert manager.latest() == 3


def test_latest_returns_none_when_empty(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    assert manager.latest() is None


def test_remove(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    manager.save(step=1, state={"w": 1})
    manager.remove(1)
    assert not os.path.exists(os.path.join(str(tmp_path), "ckpt_1.json"))


def test_checkpoint_atomic_write(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    path = manager.save(step=10, state={"value": 42})
    assert not os.path.exists(path + ".tmp")
    assert os.path.exists(path)
