from dataclasses import dataclass, field
from math import sqrt
from random import sample, seed
from typing import List, Optional, Sequence, Tuple


@dataclass
class MaskedAutoencoderConfig:
    input_dim: int = 16
    hidden_dim: int = 8
    mask_ratio: float = 0.3
    seed: Optional[int] = None


@dataclass
class MaskedAutoencoder:
    config: MaskedAutoencoderConfig = field(default_factory=MaskedAutoencoderConfig)
    _w_enc: List[List[float]] = field(init=False, default_factory=list)
    _b_enc: List[float] = field(init=False, default_factory=list)
    _w_dec: List[List[float]] = field(init=False, default_factory=list)
    _b_dec: List[float] = field(init=False, default_factory=list)
    _trained: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if self.config.seed is not None:
            seed(self.config.seed)
        dim = self.config.input_dim
        h = self.config.hidden_dim
        self._w_enc = [[(_small_random()) for _ in range(h)] for _ in range(dim)]
        self._b_enc = [0.0] * h
        self._w_dec = [[(_small_random()) for _ in range(dim)] for _ in range(h)]
        self._b_dec = [0.0] * dim

    @staticmethod
    def _relu(x: float) -> float:
        return max(0.0, x)

    @staticmethod
    def _relu_vector(x: List[float]) -> List[float]:
        return [max(0.0, v) for v in x]

    @staticmethod
    def _matmul(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        m = len(a)
        n = len(b[0])
        p = len(b)
        out = [[sum(a[i][k] * b[k][j] for k in range(p)) for j in range(n)] for i in range(m)]
        return out

    @staticmethod
    def _matmul_vec(a: List[List[float]], b: List[float]) -> List[float]:
        return [sum(a[i][j] * b[j] for j in range(len(b))) for i in range(len(a))]

    @staticmethod
    def _add_bias(m: List[List[float]], b: List[float]) -> List[List[float]]:
        return [[m[i][j] + b[j] for j in range(len(m[0]))] for i in range(len(m))]

    @staticmethod
    def _transpose(m: List[List[float]]) -> List[List[float]]:
        return [[m[j][i] for j in range(len(m))] for i in range(len(m[0]))]

    def mask(self, x: Sequence[float]) -> Tuple[List[float], List[int]]:
        length = len(x)
        num_masked = max(1, int(length * self.config.mask_ratio))
        indices = sample(range(length), num_masked)
        masked = list(x)
        for idx in indices:
            masked[idx] = 0.0
        return masked, indices

    def encode(self, x: List[List[float]]) -> List[List[float]]:
        h = self._add_bias(self._matmul(x, self._w_enc), self._b_enc)
        return [self._relu_vector(row) for row in h]

    def decode(self, h: List[List[float]]) -> List[List[float]]:
        return self._add_bias(self._matmul(h, self._w_dec), self._b_dec)

    def reconstruct(self, x: List[float]) -> List[List[float]:
        indices = list(range(len(x) // self.config.input_dim * self.config.input_dim))
        seq = [list(x[i: i + self.config.input_dim]) for i in range(0, len(x), self.config.input_dim) if i + self.config.input_dim <= len(x)]
        if not seq:
            return []
        masked = [self.mask(row)[0] for row in seq]
        enc = self.encode(masked)
        return self.decode(enc)

    def reconstruction_loss(self, original: List[List[float]], reconstructed: List[List[float]], mask_indices: List[List[int]]) -> float:
        total = 0.0
        count = 0
        for i, row in enumerate(original):
            for j, v in enumerate(row):
                if j in (mask_indices[i] if i < len(mask_indices) else []):
                    total += (v - reconstructed[i][j]) ** 2
                    count += 1
        return sqrt(total / count) if count else 0.0

    def fit(self, x: List[List[float]]) -> None:
        lr = 0.05
        for _ in range(3):
            masked = [self.mask(row)[0] for row in x]
            enc = self.encode(masked)
            dec = self.decode(enc)
            indices = [list(range(len(row))) for row in x]
            loss = self.reconstruction_loss(x, dec, indices)
            dec_t = self._transpose(dec)
            x_t = self._transpose(x)
            enc_t = self._transpose(enc)
            grad = [[2.0 * (dec[i][j] - x[i][j]) / len(x) for j in range(len(x[0]))] for i in range(len(x))]
            grad_t = self._transpose(grad)
            dw_dec = self._matmul(self._transpose(enc), grad_t)
            db_dec = [sum(grad[i][j] for i in range(len(grad))) for j in range(len(grad[0]))]
            for i in range(len(self._w_dec)):
                for j in range(len(self._w_dec[0])):
                    self._w_dec[i][j] -= lr * dw_dec[i][j]
            for j in range(len(self._b_dec)):
                self._b_dec[j] -= lr * db_dec[j]
            for i in range(len(self._w_enc)):
                for j in range(len(self._w_enc[0])):
                    self._w_enc[i][j] -= lr * 0.01
        self._trained = True

    def encode_sequence(self, x: List[List[float]) -> List[List[float]]:
        return self.encode(x)

    def decode_sequence(self, h: List[List[float]) -> List[List[float]]:
        return self.decode(h)

    def reconstruct_sequence(self, x: List[List[float]) -> List[List[float]]:
        enc = self.encode(x)
        return self.decode(enc)


def _small_random() -> float:
    return (sample(range(100), 1)[0] / 10000.0) - 0.005
