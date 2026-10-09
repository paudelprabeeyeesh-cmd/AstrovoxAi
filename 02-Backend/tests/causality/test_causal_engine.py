import pytest
import numpy as np
from causality.causal_engine import CausalEngine
from causality.causal_graph import CausalNode, CausalEdge


class TestCausalEngine:
    def test_add_node_and_edge(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        assert len(engine.nodes) == 2
        assert len(engine.edges) == 1
        assert engine.adjacency["t"] == [("y", 0.8)]

    def test_learn_from_interventions(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.0))
        avg = engine.learn_from_interventions(
            [("t", 2.0)],
            [("y", 1.6)],
        )
        assert avg == pytest.approx(0.8)
        assert engine.edges[0].strength == pytest.approx(0.8)

    def test_learn_from_interventions_mismatch_raises(self):
        engine = CausalEngine()
        with pytest.raises(ValueError):
            engine.learn_from_interventions([("t", 2.0)], [])

    def test_learn_from_interventions_no_match_returns_zero(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        avg = engine.learn_from_interventions(
            [("t", 2.0)],
            [("y", 1.0)],
        )
        assert avg == 0.0

    def test_intervention_effect_positive(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        effect = engine.intervention_effect("y", "t", 2.0)
        assert effect == pytest.approx(1.6)

    def test_intervention_effect_negative(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="negative"))
        effect = engine.intervention_effect("y", "t", 2.0)
        assert effect == pytest.approx(-1.6)

    def test_intervention_effect_no_path(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        assert engine.intervention_effect("y", "t", 2.0) == 0.0

    def test_intervention_effect_missing_node(self):
        engine = CausalEngine()
        assert engine.intervention_effect("missing", "t", 2.0) == 0.0

    def test_backdoor_adjustment(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.9))
        engine.add_edge(CausalEdge(source="c", target="t", strength=0.5))
        engine.add_edge(CausalEdge(source="c", target="y", strength=0.5))
        result = engine.backdoor_adjustment("t", "y", ["c"])
        assert result == pytest.approx(0.9 - 0.25)

    def test_backdoor_adjustment_no_direct_edge(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        assert engine.backdoor_adjustment("t", "y", ["c"]) == 0.0

    def test_counterfactual(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="positive"))
        value = engine.counterfactual({"t": 2.0}, "y")
        assert value == pytest.approx(1.6)

    def test_counterfactual_missing_target(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        assert engine.counterfactual({"t": 2.0}, "missing") is None

    def test_counterfactual_negative_sign(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.8, sign="negative"))
        value = engine.counterfactual({"t": 2.0}, "y")
        assert value == pytest.approx(-1.6)

    def test_causal_strength(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.7))
        assert engine.causal_strength("t", "y") == pytest.approx(0.7)
        assert engine.causal_strength("y", "t") == 0.0

    def test_learn_from_interventions_clamped(self):
        engine = CausalEngine()
        engine.add_node(CausalNode(id="t", variable="Treatment"))
        engine.add_node(CausalNode(id="y", variable="Outcome"))
        engine.add_edge(CausalEdge(source="t", target="y", strength=0.0))
        engine.learn_from_interventions(
            [("t", 1.0)],
            [("y", 2.0)],
        )
        assert engine.edges[0].strength == pytest.approx(1.0)
