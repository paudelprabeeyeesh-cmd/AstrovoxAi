import pytest
from world_model.mental_simulation import TheoryOfMind, MentalSimulator


class TestTheoryOfMind:
    def test_observe_creates_hypothesis(self):
        tom = TheoryOfMind()
        tom.observe("agent1", "pick_up", {"object": "ball"})
        assert "agent1" in tom.hypotheses

    def test_infer_belief_default(self):
        tom = TheoryOfMind()
        val = tom.infer_belief("agent1", "ball_is_red")
        assert val == 0.5

    def test_update_hypothesis(self):
        tom = TheoryOfMind()
        tom.update_hypothesis("agent1", "ball_is_red", 0.9)
        assert tom.hypotheses["agent1"].mental_state.beliefs["ball_is_red"] == 0.9

    def test_infer_intention_none_without_intentions(self):
        tom = TheoryOfMind()
        assert tom.infer_intention("agent1") is None


class TestMentalSimulator:
    def test_simulate_plan(self):
        tom = TheoryOfMind()
        tom.observe("agent1", "move", {})
        sim = MentalSimulator(tom)
        plan = sim.simulate_plan("agent1", ["jump", "run"], {})
        assert len(plan) == 2
        assert all("likelihood" in p for p in plan)

    def test_simulate_dialogue(self):
        tom = TheoryOfMind()
        tom.observe("agent1", "speak", {})
        sim = MentalSimulator(tom)
        dialogue = sim.simulate_dialogue("agent1", turns=2)
        assert len(dialogue) == 2
