import numpy as np
from alignment.reward_hacking import evasion_score, sycophancy_score, verbosity_score


class TestRewardHacking:
    def test_sycophancy_perfect_correlation(self):
        rewards = np.array([1.0, 2.0, 3.0, 4.0])
        similarity = np.array([1.0, 2.0, 3.0, 4.0])
        score = sycophancy_score(rewards, similarity)
        assert np.isclose(score, 1.0)

    def test_sycophancy_anti_correlation(self):
        rewards = np.array([1.0, 2.0, 3.0, 4.0])
        similarity = np.array([4.0, 3.0, 2.0, 1.0])
        score = sycophancy_score(rewards, similarity)
        assert np.isclose(score, -1.0)

    def test_verbosity_perfect_correlation(self):
        rewards = np.array([1.0, 2.0, 3.0, 4.0])
        lengths = np.array([10.0, 20.0, 30.0, 40.0])
        score = verbosity_score(rewards, lengths)
        assert np.isclose(score, 1.0)

    def test_evasion_score_range(self):
        rewards = np.array([0.5, 0.8, 0.3])
        refusal = np.array([1.0, 0.0, 1.0])
        score = evasion_score(rewards, refusal)
        assert 0.0 <= score <= 1.0

    def test_evasion_zero_refusal(self):
        rewards = np.array([0.5, 0.8])
        refusal = np.array([0.0, 0.0])
        score = evasion_score(rewards, refusal)
        assert np.isclose(score, 0.0)
