import unittest

from world_model.mental_simulation import MentalSimulator, MentalState, TheoryOfMind


class TestMentalState(unittest.TestCase):
    def test_defaults(self):
        ms = MentalState()
        self.assertEqual(ms.beliefs, {})
        self.assertEqual(ms.desires, [])
        self.assertEqual(ms.intentions, [])


class TestTheoryOfMind(unittest.TestCase):
    def test_observe_creates_hypothesis(self):
        tom = TheoryOfMind()
        tom.observe("a1", "move", {"loc": "room"})
        self.assertIn("a1", tom.hypotheses)

    def test_infer_belief_not_observed(self):
        tom = TheoryOfMind()
        self.assertEqual(tom.infer_belief("x", "p"), 0.5)

    def test_infer_belief_set(self):
        tom = TheoryOfMind()
        tom.observe("a1", "act", {})
        tom.hypotheses["a1"].mental_state.beliefs["p"] = 0.8
        self.assertAlmostEqual(tom.infer_belief("a1", "p"), 0.8)

    def test_infer_intention_none(self):
        tom = TheoryOfMind()
        self.assertIsNone(tom.infer_intention("x"))

    def test_infer_intention_set(self):
        tom = TheoryOfMind()
        tom.observe("a1", "act", {})
        tom.hypotheses["a1"].mental_state.intentions.append("intent1")
        self.assertEqual(tom.infer_intention("a1"), "intent1")

    def test_predict_next_action_no_intention(self):
        tom = TheoryOfMind()
        tom.observe("a1", "act", {})
        self.assertIsNone(tom.predict_next_action("a1"))

    def test_update_hypothesis(self):
        tom = TheoryOfMind()
        tom.update_hypothesis("a1", "k", 0.9)
        self.assertIn("a1", tom.hypotheses)
        self.assertEqual(tom.hypotheses["a1"].mental_state.beliefs["k"], 0.9)


class TestMentalSimulator(unittest.TestCase):
    def test_simulate_plan(self):
        tom = TheoryOfMind()
        sim = MentalSimulator(tom)
        plan = sim.simulate_plan("a1", ["go"], {})
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["likelihood"], 0.5)

    def test_simulate_plan_with_belief(self):
        tom = TheoryOfMind()
        tom.observe("a1", "act", {})
        sim = MentalSimulator(tom)
        plan = sim.simulate_plan("a1", ["go"], {})
        self.assertEqual(plan[0]["likelihood"], 0.5)

    def test_simulate_dialogue(self):
        tom = TheoryOfMind()
        tom.observe("a1", "act", {})
        sim = MentalSimulator(tom)
        turns = sim.simulate_dialogue("a1", turns=2)
        self.assertEqual(len(turns), 2)
        self.assertIsNone(turns[0]["intention"])


if __name__ == "__main__":
    unittest.main()
