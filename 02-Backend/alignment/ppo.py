import numpy as np
from alignment.kl_penalty import kl_penalty


def clipped_surrogate(
    ratio: np.ndarray,
    advantages: np.ndarray,
    epsilon: float,
) -> np.ndarray:
    surr1 = ratio * advantages
    surr2 = np.clip(ratio, 1.0 - epsilon, 1.0 + epsilon) * advantages
    return -np.minimum(surr1, surr2)


def value_loss(predicted: np.ndarray, target: np.ndarray) -> np.ndarray:
    return np.mean((predicted - target) ** 2)


def compute_gae(
    rewards: np.ndarray,
    values: np.ndarray,
    dones: np.ndarray,
    gamma: float = 0.99,
    lam: float = 0.95,
) -> np.ndarray:
    advantages = np.zeros_like(rewards)
    last_gae = 0.0
    for t in reversed(range(len(rewards))):
        mask = 1.0 - dones[t]
        delta = rewards[t] + gamma * values[t + 1] * mask - values[t]
        advantages[t] = last_gae = delta + gamma * lam * mask * last_gae
    return advantages


def ppo_loss(
    log_probs_new: np.ndarray,
    log_probs_old: np.ndarray,
    advantages: np.ndarray,
    values_pred: np.ndarray,
    values_target: np.ndarray,
    log_probs_ref: np.ndarray,
    beta: float = 0.1,
    epsilon: float = 0.2,
) -> dict:
    ratio = np.exp(log_probs_new - log_probs_old)
    policy_loss = np.mean(clipped_surrogate(ratio, advantages, epsilon))
    val_loss = value_loss(values_pred, values_target)
    kl = np.mean(kl_penalty(log_probs_new, log_probs_ref, beta))
    total_loss = policy_loss + 0.5 * val_loss + kl
    return {
        "total_loss": total_loss,
        "policy_loss": policy_loss,
        "value_loss": val_loss,
        "kl_penalty": kl,
    }
