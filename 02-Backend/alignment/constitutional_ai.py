import numpy as np


def generate_responses(prompt_embeddings: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    logits = prompt_embeddings / temperature
    probs = np.exp(logits - np.max(logits, axis=-1, keepdims=True))
    probs = probs / np.sum(probs, axis=-1, keepdims=True)
    return probs


def critique(responses: np.ndarray, threshold: float = 0.3) -> np.ndarray:
    entropy = -np.sum(responses * np.log(responses + 1e-8), axis=-1)
    return entropy < threshold


def revise(responses: np.ndarray, mask: np.ndarray, temperature: float = 0.5) -> np.ndarray:
    revised = np.where(mask[:, None], responses, generate_responses(responses, temperature))
    return revised / np.sum(revised, axis=-1, keepdims=True)


def train_on_revisions(original: np.ndarray, revised: np.ndarray) -> float:
    return float(np.mean((original - revised) ** 2))
