"""Tests for checkpointing and fault recovery utilities."""

from __future__ import annotations

import json

import pytest

from astrovox.checkpointing import CheckpointManager, CheckpointMetadata, JobTracker


def test_checkpoint_manager_save_and_latest(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    name = manager.save(step=10, epoch=1, loss=0.5, weights={"w": [1, 2]})
    latest = manager.latest()
    assert latest is not None
    assert latest.step == 10
    assert latest.loss == 0.5
    assert latest.path.endswith(name + ".json")


def test_checkpoint_manager_recover_returns_weights(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    manager.save(step=5, epoch=1, loss=1.0, weights={"w": [3, 4]})
    recovered = manager.recover()
    assert recovered is not None
    assert recovered["w"] == [3, 4]


def test_job_tracker_persists_state(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    tracker = JobTracker(manager)
    tracker.update(status="running", epoch=1)
    path = manager.directory / "job_state.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "running"


def test_job_tracker_fail_records_reason(tmp_path):
    manager = CheckpointManager(directory=str(tmp_path))
    tracker = JobTracker(manager)
    tracker.fail("oom")
    data = json.loads((manager.directory / "job_state.json").read_text(encoding="utf-8"))
    assert data["status"] == "failed"
    assert data["failure_reason"] == "oom"
