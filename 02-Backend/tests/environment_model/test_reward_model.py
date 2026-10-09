from world_model.environment_model import RewardModel


class TestRewardModel:
    def test_compute_returns_float(self):
        model = RewardModel(weights=[1.0, -1.0])
        reward = model.compute([1.0, 2.0], [0.5, 0.0])
        assert isinstance(reward, float)

    def test_linear_state_reward(self):
        model = RewardModel(weights=[1.0, 0.0])
        reward = model.compute([2.0, 0.0], [0.0, 0.0])
        assert reward == 2.0

    def test_action_penalty(self):
        model = RewardModel(weights=[0.0, 0.0])
        reward = model.compute([0.0, 0.0], [1.0, 0.0])
        assert reward == -0.1
