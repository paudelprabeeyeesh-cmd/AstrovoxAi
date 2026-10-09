import unittest

from world_model.agent_modeling import AgentModel, Belief, Intention


class TestBelief(unittest.TestCase):
    def test_defaults(self):
        b = Belief(proposition="p")
        self.assertEqual(b.proposition, "p")
        self.assertEqual(b.confidence, 0.5)
        self.assertEqual(b.evidence, [])
        self.assertEqual(b.last_updated, 0)

    def test_update(self):
        b = Belief(proposition="p", confidence=0.5)
        b.update(0.9, "e1")
        self.assertGreater(b.confidence, 0.5)
        self.assertIn("e1", b.evidence)
        self.assertEqual(b.last_updated, 1)

    def test_update_clamped(self):
        b = Belief(proposition="p")
        b.update(2.0, "e1")
        self.assertLessEqual(b.confidence, 1.0)
        b.update(-1.0, "e2")
        self.assertGreaterEqual(b.confidence, 0.0)


class TestAgentModel(unittest.TestCase):
    def test_defaults(self):
        model = AgentModel("a1")
        self.assertEqual(model.agent_id, "a1")
        self.assertEqual(model.traits["risk"], 0.5)
        self.assertEqual(model.beliefs, {})
        self.assertEqual(model.intentions, [])

    def test_custom_traits(self):
        model = AgentModel("a1", traits={"risk": 0.9})
        self.assertEqual(model.traits["risk"], 0.9)

    def test_set_and_get_belief(self):
        model = AgentModel("a1")
        model.set_belief("b1", 0.9)
        belief = model.get_belief("b1")
        self.assertIsNotNone(belief)
        self.assertAlmostEqual(belief.confidence, 0.7 * 0.5 + 0.3 * 0.9, places=4)

    def test_add_intention(self):
        model = AgentModel("a1")
        model.add_intention("act1", priority=0.9)
        self.assertEqual(len(model.intentions), 1)
        self.assertEqual(model.intentions[0].action, "act1")

    def test_select_action_empty(self):
        model = AgentModel("a1")
        self.assertIsNone(model.select_action())

    def test_select_action_top(self):
        model = AgentModel("a1")
        model.add_intention("low", priority=0.1)
        model.add_intention("high", priority=0.9)
        chosen = model.select_action()
        self.assertEqual(chosen.action, "high")

    def test_belief_distribution(self):
        model = AgentModel("a1")
        model.set_belief("b1", 1.0)
        dist = model.belief_distribution()
        self.assertIn("b1", dist)
        self.assertAlmostEqual(dist["b1"], 0.7 * 0.5 + 0.3 * 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
