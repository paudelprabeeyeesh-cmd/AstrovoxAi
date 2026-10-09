import pytest
from curriculum_learning_advanced.reward_shaping import RewardShaper, RewardConfig


class TestRewardShaper:
    def test_initialization(self):
        shaper = RewardShaper()
        stats = shaper.get_shaping_stats()
        assert stats["count"] == 0

    def test_shape_reward(self):
        shaper = RewardShaper(RewardConfig(gamma=1.0))
        state = {"score": 1.0}
        next_state = {"score": 2.0}
        shaped = shaper.shape_reward(0.5, state, next_state)
        assert shaped == 1.5
        assert len(shaper.history) == 1

    def test_stats(self):
        shaper = RewardShaper()
        for i in range(5):
            shaper.shape_reward(float(i), {"score": 0.0}, {"score": 0.0})
        stats = shaper.get_shaping_stats()
        assert stats["count"] == 5
        assert stats["mean"] == 2.0
