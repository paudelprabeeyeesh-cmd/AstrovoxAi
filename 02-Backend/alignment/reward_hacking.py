import numpy as np


def sycophancy_score(rewards: np.ndarray, prompt_similarity: np.ndarray) -> np.ndarray:
    return np.corrcoef(rewards, prompt_similarity)[0, 1]


def verbosity_score(rewards: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    return np.corrcoef(rewards, lengths)[0, 1]


def evasion_score(rewards: np.ndarray, refusal_indicators: np.ndarray) -> np.ndarray:
    return float(np.mean(rewards * refusal_indicators))
