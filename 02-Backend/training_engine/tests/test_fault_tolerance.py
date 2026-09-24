import numpy as np
import pytest
import os
from training_engine.fault_tolerance import FaultTolerantTrainer, CheckpointManager


def test_checkpoint_save_and_load(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    p = [np.array([1.0, 2.0, 3.0])]
    manager.save(step=1, params=p, optimizer_state={})
    step, loaded = manager.load(1)
    assert step == 1
    assert np.allclose(loaded[0], p[0])


def test_fault_tolerant_restart(tmp_path):
    trainer = FaultTolerantTrainer([np.array([1.0])], checkpoint_dir=str(tmp_path))
    trainer.checkpoint(step=5, optimizer_state={})
    step, params = trainer.restart()
    assert step == 5
    assert np.allclose(params[0], np.array([1.0]))


def test_heartbeat():
    trainer = FaultTolerantTrainer([np.array([1.0])])
    assert trainer.heartbeat() is True
