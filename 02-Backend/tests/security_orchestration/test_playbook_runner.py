from security_orchestration.playbook_runner import Playbook, PlaybookRunner


def test_run_basic_steps() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="Basic", steps=[
        {"name": "log", "action": "log"},
        {"name": "block", "action": "block"},
        {"name": "remediate", "action": "remediate"},
    ], threshold=0.5)
    incident = {"severity": 2.0, "source": "10.0.0.1"}
    result = runner.run(pb, incident)
    assert result["playbook"] == "pb1"
    assert result["status"] == "resolved"
    assert result["outputs"]["log"] == incident
    assert result["outputs"]["block"] == "10.0.0.1"
    assert result["errors"] == []


def test_run_history() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="H", steps=[{"action": "log"}], threshold=0.0)
    runner.run(pb, {"severity": 1.0})
    runner.run(pb, {"severity": 2.0})
    history = runner.history(limit=1)
    assert len(history) == 1
    assert history[0]["playbook_id"] == "pb1"


def test_run_escalate_step_raises() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="Esc", steps=[{"name": "escalate", "action": "escalate"}], threshold=0.0)
    result = runner.run(pb, {"severity": 1.0})
    assert result["status"] == "partial"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["step"] == "escalate"


def test_run_notify_step() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="Notify", steps=[
        {"name": "notify", "action": "notify", "message": "Alert!"},
    ], threshold=0.0)
    result = runner.run(pb, {"severity": 1.0})
    assert result["outputs"]["notify"] == {"notified": True, "message": "Alert!"}


def test_run_unknown_step() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="Unknown", steps=[{"name": "x", "action": "unknown"}], threshold=0.0)
    result = runner.run(pb, {"severity": 1.0})
    assert result["outputs"]["x"] is None


def test_run_malformed_step() -> None:
    runner = PlaybookRunner()
    pb = Playbook(id="pb1", name="Bad", steps=[{"name": "step1"}], threshold=0.0)
    result = runner.run(pb, {"severity": 1.0})
    assert result["status"] == "resolved"
    assert result["outputs"]["step1"] is None
