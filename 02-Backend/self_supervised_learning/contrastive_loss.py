import math
from dataclasses import dataclass
from typing import List, Union

Number = Union[int, float]
Vector = List[Number]
Matrix = List[List[Number]]


def _dot(a: Vector, b: Vector) -> Number:
    return sum(x * y for x, y in zip(a, b))


def _norm(a: Vector) -> float:
    return math.sqrt(sum(x * x for x in a)) + 1e-12


def cosine_similarity(a: Vector, b: Vector) -> float:
    denom = _norm(a) * _norm(b)
    return _dot(a, b) / denom


def cosine_similarity_matrix(vectors: List[Vector]) -> Matrix:
    n = len(vectors)
    norms = [_norm(v) for v in vectors]
    return [[_dot(vectors[i], vectors[j]) / (norms[i] * norms[j]) for j in range(n)] for i in range(n)]


@dataclass
class NTXentConfig:
    temperature: float = 0.1


def nt_xent_loss(z_i: List[Vector], z_j: List[Vector], temperature: float = 0.1) -> float:
    assert len(z_i) == len(z_j), "Batch sizes must match"
    N = len(z_i)
    z = z_i + z_j
    sim_matrix = cosine_similarity_matrix(z)
    total_loss = 0.0
    for i in range(2 * N):
        pos_idx = i + N if i < N else i - N
        logits = [s / temperature for s in sim_matrix[i]]
        max_logit = max(logits)
        exps = [math.exp(l - max_logit) for l in logits]
        sum_exps = sum(exps)
        total_loss += -math.log(exps[pos_idx] / sum_exps + 1e-12)
    return total_loss / (2 * N)


@dataclass
class InfoNCEConfig:
    temperature: float = 0.1


def info_nce_loss(query: Vector, positive: Vector, negatives: List[Vector], temperature: float = 0.1) -> float:
    sim_pos = cosine_similarity(query, positive)
    sim_negs = [cosine_similarity(query, neg) for neg in negatives]
    logits = [sim_pos / temperature] + [s / temperature for s in sim_negs]
    max_logit = max(logits)
    exps = [math.exp(l - max_logit) for l in logits]
    return -math.log(exps[0] / sum(exps) + 1e-12)
