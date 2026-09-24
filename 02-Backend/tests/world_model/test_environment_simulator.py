import unittest

from world_model.environment_simulator import EnvironmentSimulator, EnvironmentState


class TestEnvironmentSimulator(unittest.TestCase):
    def test_register_entity(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1", {"x": 0.0})
        self.assertIn("e1", sim.entities())

    def test_register_duplicate_raises(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        with self.assertRaises(ValueError):
            sim.register_entity("e1")

    def test_remove_entity(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        sim.remove_entity("e1")
        self.assertNotIn("e1", sim.entities())

    def test_set_and_get_property(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        sim.set_property("e1", "temperature", 22.5)
        self.assertEqual(sim.get_property("e1", "temperature"), 22.5)
        self.assertIsNone(sim.get_property("e1", "missing"))
        self.assertEqual(sim.get_property("e1", "missing", 0.0), 0.0)

    def test_step_advances_time(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        sim.step()
        state = sim.state()
        self.assertEqual(state.time_step, 1)

    def test_history(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        sim.step()
        sim.step()
        self.assertEqual(len(sim.history()), 2)

    def test_reset(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        sim.step()
        sim.reset()
        self.assertEqual(sim.entities(), [])
        self.assertEqual(sim.history(), [])

    def test_callback_invoked_on_step(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1")
        calls = []

        def callback(simulator: EnvironmentSimulator) -> None:
            calls.append(simulator.state().time_step)

        sim.add_callback(callback)
        sim.step()
        self.assertEqual(calls, [0])

    def test_state_snapshot(self):
        sim = EnvironmentSimulator()
        sim.register_entity("e1", {"x": 1.0})
        sim.set_property("e1", "y", 2.0)
        state = sim.state()
        self.assertIn("e1", state.entities)
        self.assertIn("e1", state.properties)
        self.assertEqual(state.properties["e1"]["y"], 2.0)


if __name__ == "__main__":
    unittest.main()
