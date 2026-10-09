import unittest

from world_model.environment_model import StateObserver


class TestStateObserver(unittest.TestCase):
    def test_record(self):
        obs = StateObserver()
        state = obs.record([0.0, 1.0, 2.0])
        self.assertIsNotNone(state)
        self.assertEqual(obs.get_history()[0], state)

    def test_record_multiple(self):
        obs = StateObserver()
        obs.record([0.0, 1.0])
        obs.record([2.0, 3.0])
        self.assertEqual(len(obs.get_history()), 2)

    def test_get_history_independent(self):
        obs = StateObserver()
        obs.record([0.0])
        h1 = obs.get_history()
        h2 = obs.get_history()
        self.assertIsNot(h1, h2)

    def test_record_increments_time_step(self):
        obs = StateObserver()
        s0 = obs.record([0.0])
        s1 = obs.record([1.0])
        self.assertEqual(s0.time_step, 0)
        self.assertEqual(s1.time_step, 1)

    def test_record_entity_length(self):
        obs = StateObserver()
        s = obs.record([0.0, 0.0, 0.0])
        self.assertEqual(len(s.entities["env"]), 3)


if __name__ == "__main__":
    unittest.main()
