from agi_core.self_awareness import SelfAwarenessEngine


class TestSelfAwarenessEngine:
    def test_assess_capabilities(self):
        engine = SelfAwarenessEngine()
        score = engine.assess_capabilities("reasoning", 0.8)
        assert 0.0 <= score <= 1.0
        assert engine.model.capabilities["reasoning"] == 0.8

    def test_recognize_limitations(self):
        engine = SelfAwarenessEngine()
        lims = engine.recognize_limitations(["memory_overload"])
        assert "memory_overload" in lims
        assert len(lims) == 1

    def test_self_monitor(self):
        engine = SelfAwarenessEngine()
        engine.assess_capabilities("c1", 0.7)
        engine.recognize_limitations(["l1"])
        report = engine.self_monitor()
        assert "capability_level" in report
        assert report["capability_level"] > 0.0

    def test_self_model_property(self):
        engine = SelfAwarenessEngine()
        engine.assess_capabilities("m1", 0.5)
        model = engine.get_self_model()
        assert isinstance(model.capabilities, dict)
