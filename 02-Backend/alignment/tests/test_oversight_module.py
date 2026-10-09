from alignment.oversight_module import OversightModule


class TestOversightModule:
    def test_compute_risk_score_empty(self):
        om = OversightModule()
        assert om.compute_risk_score({}) == 0.0

    def test_needs_intervention_below_threshold(self):
        om = OversightModule(intervention_threshold=0.9)
        assert not om.needs_intervention({"impact": 0.1})

    def test_needs_intervention_above_threshold(self):
        om = OversightModule(intervention_threshold=0.1)
        assert om.needs_intervention({"impact": 0.5})

    def test_log_action_audit_entry(self):
        om = OversightModule(intervention_threshold=1.0)
        entry = om.log_action("act_1", {"impact": 0.3})
        assert entry["action_id"] == "act_1"
        assert entry["intervention"] is False

    def test_log_action_triggers_intervention(self):
        om = OversightModule(intervention_threshold=0.0)
        entry = om.log_action("act_1", {"impact": 0.3})
        assert entry["intervention"] is True
        assert len(om.intervention_log) == 1

    def test_review_deviations_empty(self):
        om = OversightModule()
        assert om.review_deviations() == []

    def test_review_deviations_filters(self):
        om = OversightModule(intervention_threshold=0.0)
        om.log_action("a1", {"impact": 0.9})
        om.log_action("a2", {"impact": 0.1})
        deviations = om.review_deviations(acceptable_threshold=0.2)
        assert len(deviations) == 1

    def test_audit_coverage_empty(self):
        om = OversightModule()
        assert om.audit_coverage() == 0.0

    def test_audit_coverage_after_log(self):
        om = OversightModule()
        om.log_action("a1", {"impact": 0.1})
        assert om.audit_coverage() == 1.0

    def test_intervention_effectiveness_no_interventions(self):
        om = OversightModule(intervention_threshold=1.0)
        om.log_action("a1", {"impact": 0.1})
        assert om.intervention_effectiveness() == 1.0

    def test_oversight_report_keys(self):
        om = OversightModule()
        om.log_action("a1", {"impact": 0.1})
        report = om.oversight_report()
        assert "total_actions" in report
        assert "intervention_effectiveness" in report
