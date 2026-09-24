import numpy as np


def kl_divergence(log_prob_policy: np.ndarray, log_prob_ref: np.ndarray) -> np.ndarray:
    return np.sum(np.exp(log_prob_policy) * (log_prob_policy - log_prob_ref), axis=-1)


def kl_penalty(log_prob_policy: np.ndarray, log_prob_ref: np.ndarray, beta: float) -> np.ndarray:
    return beta * kl_divergence(log_prob_policy, log_prob_ref)
