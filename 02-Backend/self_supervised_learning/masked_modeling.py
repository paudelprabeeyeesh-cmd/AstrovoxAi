import random
import math
from dataclasses import dataclass
from typing import List, Tuple, Union, Optional

Number = Union[int, float]
Vector = List[Number]
Sequence = List[Union[str, Number]]


@dataclass
class MaskedModelingConfig:
    mask_ratio: float = 0.3
    mask_token: str = "<MASK>"


def mask_sequence(sequence: Sequence, config: Optional[MaskedModelingConfig] = None) -> Tuple[Sequence, List[int]]:
    if config is None:
        config = MaskedModelingConfig()
    length = len(sequence)
    num_masked = max(1, int(length * config.mask_ratio))
    indices = random.sample(range(length), num_masked)
    masked = list(sequence)
    for idx in indices:
        masked[idx] = config.mask_token
    return masked, indices


def mask_float_vector(x: Vector, mask_ratio: float = 0.3) -> Tuple[Vector, Vector, List[int]]:
    dim = len(x)
    num_masked = max(1, int(dim * mask_ratio))
    indices = random.sample(range(dim), num_masked)
    x_masked = [0.0 if idx in indices else float(v) for idx, v in enumerate(x)]
    target = [0.0] * dim
    for idx in indices:
        target[idx] = float(x[idx])
    return x_masked, target, indices


def reconstruction_loss(original: Vector, reconstructed: Vector, mask_indices: List[int]) -> float:
    if not mask_indices:
        return 0.0
    mse = sum((float(original[i]) - float(reconstructed[i])) ** 2 for i in mask_indices) / len(mask_indices)
    return math.sqrt(mse)
