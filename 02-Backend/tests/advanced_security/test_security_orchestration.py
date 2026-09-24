from advanced_security.security_orchestration import (
    PBACEngine,
    Playbook,
    SOARIntegration,
    SecurityOrchestrator,
    SplunkIntegration,
)


def test_playbook_lifecycle() -> None:
    orchestrator = SecurityOrchestrator()
    pb = Playbook(id="pb1", name="Test Playbook", steps=[{"action": "log"}, {"action": "block"}], threshold=1.0)
    orchestrator.add_playbook(pb)
    incident = {"severity": 5.0, "source": "1.2.3.4", "tags": ["test"]}
    result = orchestrator.incident(incident)
    assert result["status"] == "closed"
    assert result["resolution"]["playbook"] == "pb1"


def test_policy_context() -> None:
    orchestrator = SecurityOrchestrator()
    ctx = orchestrator.policy_context("user", "file")
    assert ctx["subject"] == "user"
    assert ctx["session"]


def test_splunk_integration() -> None:
    orchestrator = SecurityOrchestrator()
    integrator = SplunkIntegration()
    incidents = [{"id": "i1"}]
    results = integrator.transform(incidents)
    assert results[0]["sourcetype"] == "orchestrator"


def test_soar_integration() -> None:
    orchestrator = SecurityOrchestrator()
    pb = Playbook(id="p1", name="Playbook", steps=[{"action": "log"}], threshold=0.5)
    orchestrator.add_playbook(pb)
    soar = SOARIntegration(orchestrator)
    result = soar.trigger({"severity": 1.0, "tags": ["p1"]})
    assert result["status"] == "closed"


def test_security_orchestrator_init() -> None:
    orchestrator = SecurityOrchestrator()
    incident = {"id": "i1", "source": "1.2.3.4", "tags": ["unknown"]}
    result = orchestrator.incident(incident)
    assert result["status"] == "closed"
    assert result["resolution"]["status"] == "escalated"


def test_pbac_engine() -> None:
    pbac = PBACEngine()
    assert pbac.evaluate({}, {}, "read", {}) is False
