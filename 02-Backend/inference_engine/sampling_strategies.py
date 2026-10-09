
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Callable, Tuple, Union
import numpy as np


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def log_softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    log_sum_exp = x_max + np.log(np.sum(np.exp(x - x_max), axis=-1, keepdims=True))
    return x - log_sum_exp


def apply_temperature(logits: np.ndarray, temperature: float) -> np.ndarray:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    return logits / temperature


def top_k_logits(logits: np.ndarray, k: int) -> np.ndarray:
    if k <= 0:
        raise ValueError("top_k must be positive")
    num_tokens = logits.shape[-1]
    k = min(k, num_tokens)
    if k == num_tokens:
        return logits
    sorted_indices = np.argsort(logits, axis=-1)
    kth_smallest = float(logits[..., sorted_indices[..., 0]])
    mask = np.zeros_like(logits, dtype=bool)
    mask[sorted_indices >= sorted_indices[..., -k:k]] = False
    cutoff_idx = sorted_indices[..., -k]
    cutoff_val = np.zeros_like(logits)
    cutoff_val[..., cutoff_idx] = logits[..., cutoff_idx]
    top_k_val = np.partition(logits, -k, axis=-1)[..., -k:]
    kth_val = top_k_val[..., 0]
    result = np.where(logits < kth_val[..., None], -1e10, logits)
    return result


def top_p_logits(logits: np.ndarray, top_p: float) -> np.ndarray:
    if top_p <= 0 or top_p > 1:
        raise ValueError("top_p must be in (0, 1]")
    sorted_logits = np.sort(logits, axis=-1)[::-1]
    probs = softmax(sorted_logits)
    cumulative_probs = np.cumsum(probs, axis=-1)
    sorted_indices = np.argsort(logits, axis=-1)[::-1]
    cutoff_indices = np.searchsorted(cumulative_probs, top_p, side="right")
    cutoff_indices = np.clip(cutoff_indices, 1, len(logits))
    kth_cutoff = cutoff_indices[0] if cutoff_indices.ndim == 0 else cutoff_indices[0]
    cutoff_val = float(sorted_logits[0, kth_cutoff - 1])
    result = np.where(logits < cutoff_val, -1e10, logits)
    return result


@dataclass
class SamplingStrategy:
    strategy_type: str = "greedy"
    temperature: float = 1.0
    top_k: int = 0
    top_p: float = 1.0
    min_p: float = 0.0
    tfs: float = 1.0
    eta: float = 0.0
    seed: Optional[int] = None

    def __post_init__(self):
        if self.seed is not None:
            self._rng = np.random.default_rng(self.seed)
        else:
            self._rng = np.random.default_rng()

    def sample(
        self,
        logits: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        if self.temperature != 1.0:
            logits = apply_temperature(logits, self.temperature)
        if self.top_k > 0:
            logits = top_k_logits(logits, self.top_k)
        if self.top_p < 1.0:
            logits = top_p_logits(logits, self.top_p)
        probs = softmax(logits)
        log_probs = log_softmax(logits)
        return self._pick(probs, log_probs, return_log_probs=return_log_probs)

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return greedy_sample(probs, log_probs, return_log_probs=return_log_probs)

    def configure(
        self,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
        min_p: Optional[float] = None,
    ) -> None:
        if temperature is not None:
            self.temperature = temperature
        if top_k is not None:
            self.top_k = top_k
        if top_p is not None:
            self.top_p = top_p
        if min_p is not None:
            self.min_p = min_p

    def get_all_hyperparameters(self) -> Dict:
        return {
            "strategy_type": self.strategy_type,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "min_p": self.min_p,
            "tfs": self.tfs,
            "eta": self.eta,
            "seed": self.seed,
        }


def greedy_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    token_id = int(np.argmax(probs))
    if return_log_probs:
        return token_id, log_probs
    return token_id


def temperature_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    token_id = int(rng.choice(len(probs), p=probs))
    if return_log_probs:
        return token_id, log_probs
    return token_id


def top_k_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    k: int,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    top_k = min(k, len(probs))
    top_indices = np.argsort(probs)[-top_k:][::-1]
    top_probs = probs[top_indices]
    top_probs = top_probs / top_probs.sum()
    selected = int(rng.choice(top_indices.shape[0], p=top_probs))
    token_id = int(top_indices[selected])
    if return_log_probs:
        return token_id, log_probs
    return token_id


def top_p_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    top_p: float,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    sorted_indices = np.argsort(probs)[::-1]
    sorted_probs = probs[sorted_indices]
    cumulative = np.cumsum(sorted_probs)
    cutoff = int(np.searchsorted(cumulative, top_p)) + 1
    cutoff = min(cutoff, len(probs))
    top_indices = sorted_indices[:cutoff]
    top_probs = sorted_probs[:cutoff]
    top_probs = top_probs / top_probs.sum()
    selected = int(rng.choice(top_indices.shape[0], p=top_probs))
    token_id = int(top_indices[selected])
    if return_log_probs:
        return token_id, log_probs
    return token_id


def min_p_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    min_p: float,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    max_prob = float(np.max(probs))
    threshold = max_prob * min_p
    valid = probs >= threshold
    if not np.any(valid):
        token_id = int(np.argmax(probs))
        if return_log_probs:
            return token_id, log_probs
        return token_id
    valid_probs = probs[valid]
    valid_indices = np.where(valid)[0]
    valid_probs = valid_probs / valid_probs.sum()
    selected = int(rng.choice(valid_indices.shape[0], p=valid_probs))
    token_id = int(valid_indices[selected])
    if return_log_probs:
        return token_id, log_probs
    return token_id


def tfs_sample(
    probs: np.ndarray,
    log_probs: np.ndarray,
    tfs: float,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    sorted_indices = np.argsort(probs)[::-1]
    sorted_probs = probs[sorted_indices]
    d2_probs = np.diff(sorted_probs) ** 2
    cumulative_d2 = np.cumsum(d2_probs)
    cumulative_d2 = np.concatenate([[0.0], cumulative_d2])
    total_d2 = cumulative_d2[-1]
    if total_d2 <= 1e-10:
        token_id = int(sorted_indices[0])
        if return_log_probs:
            return token_id, log_probs
        return token_id
    cutoff = int(np.searchsorted(cumulative_d2 / total_d2, tfs)) + 1
    cutoff = min(cutoff, len(probs))
    top_indices = sorted_indices[:cutoff]
    top_probs = sorted_probs[:cutoff]
    top_probs = top_probs / top_probs.sum()
    selected = int(rng.choice(top_indices.shape[0], p=top_probs))
    token_id = int(top_indices[selected])
    if return_log_probs:
        return token_id, log_probs
    return token_id


def eta_sampling(
    probs: np.ndarray,
    log_probs: np.ndarray,
    eta: float,
    rng: np.random.Generator,
    return_log_probs: bool = False,
) -> Union[int, Tuple[int, np.ndarray]]:
    if eta <= 1e-10:
        token_id = int(np.argmax(probs))
        if return_log_probs:
            return token_id, log_probs
        return token_id
    num_probs = len(probs)
    omega = np.exp(-eta / num_probs)
    num_samples = min(num_probs, max(1, int(np.floor(omega * num_probs + 1e-10))))
    num_samples = min(num_samples, num_probs)
    if num_samples >= num_probs:
        token_id = int(rng.choice(num_probs, p=probs))
        if return_log_probs:
            return token_id, log_probs
        return token_id
    sorted_indices = np.argsort(probs)[::-1]
    top_indices = sorted_indices[:num_samples]
    top_probs = probs[top_indices]
    top_probs = top_probs / top_probs.sum()
    selected = int(rng.choice(num_samples, p=top_probs))
    token_id = int(top_indices[selected])
    if return_log_probs:
        return token_id, log_probs
    return token_id


@dataclass
class TemperatureStrategy(SamplingStrategy):
    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "temperature"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return temperature_sample(
            probs, log_probs, self._rng, return_log_probs=return_log_probs
        )


@dataclass
class TopKStrategy(SamplingStrategy):
    k: int = 50

    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "top_k"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return top_k_sample(
            probs, log_probs, self.k, self._rng, return_log_probs=return_log_probs
        )


@dataclass
class TopPStrategy(SamplingStrategy):
    p: float = 0.9

    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "top_p"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return top_p_sample(
            probs, log_probs, self.p, self._rng, return_log_probs=return_log_probs
        )


@dataclass
class MinPStrategy(SamplingStrategy):
    p: float = 0.05

    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "min_p"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return min_p_sample(
            probs, log_probs, self.p, self._rng, return_log_probs=return_log_probs
        )


@dataclass
class TFSStrategy(SamplingStrategy):
    tfs: float = 0.9

    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "tfs"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return tfs_sample(
            probs, log_probs, self.tfs, self._rng, return_log_probs=return_log_probs
        )


@dataclass
class EtaStrategy(SamplingStrategy):
    eta: float = 0.1

    def __post_init__(self):
        super().__post_init__()
        self.strategy_type = "eta"

    def _pick(
        self,
        probs: np.ndarray,
        log_probs: np.ndarray,
        return_log_probs: bool = False,
    ) -> Union[int, Tuple[int, np.ndarray]]:
        return eta_sampling(
            probs, log_probs, self.eta, self._rng, return_log_probs=return_log_probs
        )
