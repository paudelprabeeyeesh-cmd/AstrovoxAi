import numpy as np
from alignment.rlaif import aggregate_feedback, generate_ai_feedback, rlaif_reward


class TestRLAIF:
    def test_generate_feedback_shape(self):
        responses = np.random.randn(5, 8)
        reference = np.random.randn(8)
        feedback = generate_ai_feedback(responses, reference)
        assert feedback.shape == responses.shape

    def test_aggregate_feedback_mean(self):
        feedbacks = np.random.randn(3, 8)
        agg = aggregate_feedback(feedbacks)
        assert np.allclose(agg, np.mean(feedbacks, axis=0))

    def test_rlaif_reward_scalar(self):
        policy_output = np.random.randn(4)
        feedback = np.random.randn(4)
        reward = rlaif_reward(policy_output, feedback)
        assert np.isscalar(reward) or reward.shape == ()

    def test_reward_symmetry(self):
        policy_output = np.random.randn(4)
        feedback = np.random.randn(4)
        r1 = rlaif_reward(policy_output, feedback)
        r2 = rlaif_reward(feedback, policy_output)
        assert np.isfinite(r1) and np.isfinite(r2)
