import numpy as np


def bradley_terry_loss(reward_win: np.ndarray, reward_lose: np.ndarray) -> np.ndarray:
    diff = reward_win - reward_lose
    return -np.log(1.0 / (1.0 + np.exp(-diff)) + 1e-8)


def compute_rewards(logits: np.ndarray) -> np.ndarray:
    return logits
