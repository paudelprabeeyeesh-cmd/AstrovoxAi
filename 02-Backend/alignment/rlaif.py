import numpy as np


def generate_ai_feedback(responses: np.ndarray, reference: np.ndarray, noise_scale: float = 0.1) -> np.ndarray:
    return responses + noise_scale * np.random.randn(*responses.shape)


def aggregate_feedback(feedbacks: np.ndarray) -> np.ndarray:
    return np.mean(feedbacks, axis=0)


def rlaif_reward(policy_output: np.ndarray, feedback: np.ndarray) -> np.ndarray:
    return np.sum(policy_output * feedback, axis=-1)
