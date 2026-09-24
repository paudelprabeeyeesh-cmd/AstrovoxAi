from meta_learning_advanced.adaptation_step import AdaptationStep, AdaptationTracker


def test_adaptation_step_creation():
    before = {"W": 1.0}
    after = {"W": 1.1}
    step = AdaptationStep(step_idx=0, before_params=before, after_params=after, loss=1.0, grad_norm=0.5)
    assert step.step_idx == 0
    assert step.loss == 1.0
    assert step.grad_norm == 0.5
    assert step.after_params["W"] == 1.1


def test_adaptation_tracker_record_step():
    tracker = AdaptationTracker()
    before = {"W": 1.0}
    after = {"W": 1.1}
    tracker.record_step(0, before, after, loss=1.0, grad_norm=0.5)
    assert len(tracker.steps) == 1
    assert tracker.steps[0].step_idx == 0


def test_adaptation_tracker_get_trajectory():
    tracker = AdaptationTracker()
    before = {"W": 1.0}
    after = 1.1
    tracker.record_step(0, before, {"W": after}, loss=1.0, grad_norm=0.5)
    tracker.record_step(1, before, {"W": after}, loss=0.8, grad_norm=0.3)
    traj = tracker.get_trajectory()
    assert len(traj) == 2
    assert traj[0]["loss"] == 1.0
    assert traj[1]["loss"] == 0.8
    assert "param_change" in traj[0]
    assert "W" in traj[0]["param_change"]


def test_adaptation_tracker_get_summary_empty():
    tracker = AdaptationTracker()
    summary = tracker.get_summary()
    assert summary == {"num_steps": 0}


def test_adaptation_tracker_get_summary():
    tracker = AdaptationTracker()
    before = {"W": 1.0}
    after = 1.1
    tracker.record_step(0, before, {"W": after}, loss=1.0, grad_norm=0.5)
    tracker.record_step(1, before, {"W": after}, loss=0.5, grad_norm=0.2)
    summary = tracker.get_summary()
    assert summary["num_steps"] == 2
    assert summary["initial_loss"] == 1.0
    assert summary["final_loss"] == 0.5
    assert summary["loss_reduction"] == 0.5
    assert summary["mean_grad_norm"] > 0
    assert summary["max_grad_norm"] == 0.5


def test_adaptation_tracker_clear():
    tracker = AdaptationTracker()
    before = {"W": 1.0}
    tracker.record_step(0, before, {"W": 1.0}, loss=1.0, grad_norm=0.5)
    tracker.clear()
    assert len(tracker.steps) == 0
    assert tracker.get_summary() == {"num_steps": 0}


def test_adaptation_step_metadata():
    before = {"W": 1.0}
    after = {"W": 1.1}
    step = AdaptationStep(step_idx=0, before_params=before, after_params=after, loss=1.0, grad_norm=0.5, custom_key="value")
    assert step.metadata["custom_key"] == "value"
    traj = AdaptationTracker()
    traj.record_step(0, before, after, loss=1.0, grad_norm=0.5, custom_key="value")
    assert traj.steps[0].metadata["custom_key"] == "value"
