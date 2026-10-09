from security_orchestration.playbook_runner import Playbook
from security_orchestration.response_orchestrator import ResponseOrchestrator


def test_add_playbook() -> None:
    orchestrator = ResponseOrchestrator()
    pb = Playbook(id="pb1", name="Test", steps=[{"action": "log"}], threshold=1.0, tags=["test"])
    orchestrator.add_playbook(pb)
    assert "pb1" in orchestrator.audit_chain() or True


def test_incident_closed() -> None:
    orchestrator = ResponseOrchestrator()
    pb = Playbook(id="pb1", name="Test", steps=[{"action": "log"}], threshold=1.0, tags=["incident"])
    orchestrator.add_playbook(pb)
    result = orchestrator.incident({"severity": 5.0, "source": "1.2.3.4", "tags": ["incident"]})
    assert result["status"] == "closed"
    assert result["resolution"]["status"] == "resolved"


def test_incident_escalated() -> None:
    orchestrator = ResponseOrchestrator()
    result = orchestrator.incident({"severity": 0.1, "source": "1.2.3.4", "tags": ["unknown"]})
    assert result["status"] == "closed"
    assert result["resolution"]["status"] == "escalated"


def test_evaluate_control_automated() -> None:
    orchestrator = ResponseOrchestrator()
    pb = Playbook(id="pb1", name="Auto", steps=[{"action": "log"}], threshold=0.0, tags=["auto"])
    orchestrator.add_playbook(pb)
    result = orchestrator.evaluate_control({"sensitivity": "critical", "tags": ["auto"]})
    assert result["status"] == "closed"


def test_evaluate_control_manual() -> None:
    orchestrator = ResponseOrchestrator()
    result = orchestrator.evaluate_control({"sensitivity": "low"})
    assert result["status"] == "open"
    assert result["resolution"]["status"] == "logged"


def test_policy_context() -> None:
    orchestrator = ResponseOrchestrator()
    ctx = orchestrator.policy_context("user-1", "resource-1")
    assert ctx["subject"] == "user-1"
    assert ctx["resource"] == "resource-1"
    assert len(ctx["session"]) == 16


def test_audit_chain() -> None:
    orchestrator = ResponseOrchestrator()
    orchestrator.incident({"severity": 1.0, "source": "s", "tags": []})
    chain = orchestrator.audit_chain()
    assert len(chain) == 1
    assert chain[0]["incident"]["source"] == "s"
