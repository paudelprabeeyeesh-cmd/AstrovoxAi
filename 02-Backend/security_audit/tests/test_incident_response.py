"""Tests for Task 114: Incident Response."""

import numpy as np
import pytest

from security_audit.incident_response import (
    Incident,
    IncidentResponseSystem,
    Playbook,
    PlaybookStep,
)


@pytest.fixture
def irs():
    return IncidentResponseSystem()


class TestIncident:
    def test_incident_creation(self):
        irs = IncidentResponseSystem()
        incident = irs.detect(["malware detected"], ["server1"], severity="critical")
        assert incident.status == "open"
        assert incident.severity == "critical"

    def test_incident_auto_id(self, irs):
        inc1 = irs.detect(["indicator"], ["asset1"])
        inc2 = irs.detect(["indicator2"], ["asset2"])
        assert inc1.id != inc2.id
        assert inc1.id.startswith("INC-")

    def test_incident_default_response_actions(self, irs):
        incident = irs.detect([], [])
        assert incident.response_actions == []


class TestPlaybook:
    def test_playbook_step_creation(self):
        step = PlaybookStep("isolate", {"scope": "all"})
        assert step.action == "isolate"
        assert step.params == {"scope": "all"}
        assert step.auto is True

    def test_playbook_step_default_params(self):
        step = PlaybookStep("notify")
        assert step.params == {}

    def test_default_playbooks_exist(self, irs):
        assert len(irs.playbooks) > 0

    def test_malware_playbook_present(self, irs):
        pb = next((p for p in irs.playbooks if p.name == "malware_outbreak"), None)
        assert pb is not None
        assert len(pb.steps) > 0


class TestIncidentResponseSystem:
    def test_classify_malware(self, irs):
        incident = irs.detect(["ransomware detected"], ["server1"], severity="high")
        assert irs.classify(incident) == "malware"

    def test_classify_data_breach(self, irs):
        incident = irs.detect(["data exfiltration"], ["db1"], severity="critical")
        assert irs.classify(incident) == "data_breach"

    def test_classify_dos(self, irs):
        incident = irs.detect(["ddos flood detected"], ["web1"], severity="high")
        assert irs.classify(incident) == "dos"

    def test_classify_access_control(self, irs):
        incident = irs.detect(["login brute force"], ["vpn1"], severity="medium")
        assert irs.classify(incident) == "access_control"

    def test_classify_generic(self, irs):
        incident = irs.detect(["unknown anomaly"], ["host1"])
        assert irs.classify(incident) == "generic"

    def test_respond_updates_status(self, irs):
        incident = irs.detect(["malware"], ["server1"])
        irs.respond(incident)
        assert incident.status in ("contained", "investigating")

    def test_respond_adds_actions(self, irs):
        incident = irs.detect(["malware"], ["server1"])
        actions = irs.respond(incident)
        assert len(actions) > 0
        assert "isolate_asset" in actions

    def test_respond_data_breach(self, irs):
        incident = irs.detect(["data leak"], ["db1"])
        actions = irs.respond(incident)
        assert "contain_breach" in actions

    def test_get_incident(self, irs):
        incident = irs.detect(["indicator"], ["asset1"])
        fetched = irs.get_incident(incident.id)
        assert fetched is incident

    def test_get_incident_missing(self, irs):
        assert irs.get_incident("INC-999999") is None

    def test_list_incidents(self, irs):
        irs.detect(["a"], ["1"])
        irs.detect(["b"], ["2"])
        assert len(irs.list_incidents()) == 2

    def test_compute_severity_score_range(self, irs):
        incident = irs.detect(["a"], ["a", "b", "c"], severity="critical")
        score = irs.compute_severity_score(incident)
        assert 0.0 <= score <= 1.0

    def test_severity_score_critical_high(self, irs):
        incident = irs.detect(["a"], ["a", "b", "c", "d", "e"], severity="critical")
        score = irs.compute_severity_score(incident)
        assert score >= 0.5


class TestIncidentResponseSystemNumpy:
    def test_severity_scores_numeric(self, irs):
        severities = ["low", "medium", "high", "critical"]
        scores = np.array([irs.compute_severity_score(irs.detect(["x"], ["a"], severity=s)) for s in severities])
        assert scores.dtype in (np.float64, np.float32)

    def test_more_assets_higher_score(self, irs):
        low = irs.detect(["x"], ["a"], severity="critical")
        high = irs.detect(["x"], ["a", "b", "c", "d", "e"], severity="critical")
        assert irs.compute_severity_score(high) >= irs.compute_severity_score(low)

    def test_incident_id_uniqueness(self, irs):
        ids = [irs.detect(["x"], ["a"]).id for _ in range(10)]
        assert len(set(ids)) == 10

    def test_response_action_counts(self, irs):
        incident = irs.detect(["malware"], ["server1", "server2", "server3"])
        actions = irs.respond(incident)
        assert len(actions) >= len(irs.playbooks[0].steps)
