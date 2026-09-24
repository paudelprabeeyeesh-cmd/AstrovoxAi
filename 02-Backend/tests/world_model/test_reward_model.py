import unittest

from world_model.environment_model import RewardModel


class TestRewardModel(unittest.TestCase):
    def test_defaults(self):
        rm = RewardModel()
        self.assertEqual(rm.weights, [])

    def test_compute_state_only(self):
        rm = RewardModel(weights=[1.0, 2.0])
        reward = rm.compute(state=[1.0, 2.0], action=[0.0, 0.0])
        self.assertAlmostEqual(reward, 1.0 * 1.0 + 2.0 * 2.0)

    def test_compute_state_and_action(self):
        rm = RewardModel(weights=[1.0])
        reward = rm.compute(state=[2.0], action=[1.0])
        expected = 1.0 * 2.0 - 0.1 * (1.0 ** 2)
        self.assertAlmostEqual(reward, expected)

    def test_compute_mismatched_lengths(self):
        rm = RewardModel(weights=[1.0, 1.0])
        reward = rm.compute(state=[1.0], action=[0.5])
        expected = 1.0 * 1.0 - 0.1 * (0.5 ** 2)
        self.assertAlmostEqual(reward, expected)

    def test_compute_negative_reward(self):
        rm = RewardModel(weights=[-1.0])
        reward = rm.compute(state=[1.0], action=[0.0])
        self.assertAlmostEqual(reward, -1.0)

    def test_compute_empty(self):
        rm = RewardModel(weights=[])
        reward = rm.compute(state=[1.0], action=[1.0])
        self.assertAlmostEqual(reward, 0.0)


if __name__ == "__main__":
    unittest.main()
