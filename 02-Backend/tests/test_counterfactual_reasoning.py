from world_model.counterfactual_reasoning import CounterfactualReasoner


class TestCounterfactualReasoner:
    def test_record_history(self):
        cr = CounterfactualReasoner()
        events = [{"step": 0, "value": 1.0}, {"step": 1, "value": 2.0}]
        cr.record_history("h1", events)
        assert len(cr.histories["h1"]) == 2

    def test_generate_alternative(self):
        cr = CounterfactualReasoner()
        cr.record_history("h1", [{"step": 0, "value": 1.0, "reward": 0.5}])
        alt = cr.generate_alternative("h1", {"reward": 1.0})
        assert alt[0]["reward"] == 1.0
        assert len(cr.alternatives) == 1

    def test_compare(self):
        cr = CounterfactualReasoner()
        actual = [{"value": 1.0, "reward": 0.5}]
        alternative = [{"value": 2.0, "reward": 1.0}]
        diff = cr.compare(actual, alternative)
        assert diff["value"] == 1.0
        assert diff["reward"] == 0.5

    def test_decision_value(self):
        cr = CounterfactualReasoner()
        val = cr.decision_value(1.0, 3.0)
        assert val == 2.0

    def test_best_alternative_none_when_empty(self):
        cr = CounterfactualReasoner()
        assert cr.best_alternative() is None

    def test_best_alternative(self):
        cr = CounterfactualReasoner()
        cr.record_history("h1", [{"value": 1.0}])
        cr.record_history("h2", [{"value": 5.0}])
        cr.generate_alternative("h1", {"value": 10.0})
        cr.generate_alternative("h2", {"value": 1.0})
        best = cr.best_alternative()
        assert best["history_id"] == "h1"
