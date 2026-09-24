import numpy as np


def dpo_loss(
    log_prob_chosen: np.ndarray,
    log_prob_rejected: np.ndarray,
    log_prob_ref_chosen: np.ndarray,
    log_prob_ref_rejected: np.ndarray,
    beta: float = 0.1,
) -> np.ndarray:
    margin = beta * (
        (log_prob_chosen - log_prob_ref_chosen) - (log_prob_rejected - log_prob_ref_rejected)
    )
    return -np.log(1.0 / (1.0 + np.exp(-margin)) + 1e-8)


def dpo_accuracy(
    log_prob_chosen: np.ndarray,
    log_prob_rejected: np.ndarray,
    log_prob_ref_chosen: np.ndarray,
    log_prob_ref_rejected: np.ndarray,
    beta: float = 0.1,
) -> np.ndarray:
    margin = beta * (
        (log_prob_chosen - log_prob_ref_chosen) - (log_prob_rejected - log_prob_ref_rejected)
    )
    return margin > 0
