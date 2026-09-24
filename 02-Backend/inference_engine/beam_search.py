
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import numpy as np


class BeamSearchMode(Enum):
    ONE_VS_N = "one_vs_n"
    BEST_K = "best_k"


class LengthPenaltyType(Enum):
    NONE = "none"
    WU = "wu"
    LENG = "leng"


@dataclass
class BeamHypothesis:
    token_ids: List[int] = field(default_factory=list)
    log_prob: float = 0.0
    length_penalty: float = 1.0

    @property
    def score(self) -> float:
        lp = self.length_penalty
        if lp <= 0:
            return self.log_prob
        penalty = ((len(self.token_ids) + 5) / 6.0) ** lp
        return self.log_prob / penalty

    def extend(self, token_id: int, log_prob: float) -> "BeamHypothesis":
        new_hypo = BeamHypothesis(
            token_ids=self.token_ids + [token_id],
            log_prob=self.log_prob + log_prob,
            length_penalty=self.length_penalty,
        )
        return new_hypo

    def completed(self, max_length: int) -> bool:
        return len(self.token_ids) >= max_length

    def copy(self) -> "BeamHypothesis":
        return BeamHypothesis(
            token_ids=list(self.token_ids),
            log_prob=self.log_prob,
            length_penalty=self.length_penalty,
        )


def length_penalty_wu(
    length: int,
    alpha: float = 0.9
) -> float:
    if alpha < 1.0 and length > 0:
        return (5.0 + length) ** alpha / (5.0 + 1.0) ** alpha
    return length ** alpha


def length_penalty_leng(
    length: int,
    beta: float = 0.0
) -> float:
    return np.exp(beta * length)


@dataclass
class Beam:
    mode: BeamSearchMode = BeamSearchMode.BEST_K
    num_beams: int = 4
    length_penalty_type: LengthPenaltyType = LengthPenaltyType.NONE
    length_penalty_value: float = 0.0

    def __post_init__(self):
        self._hypos: List[BeamHypothesis] = [
            BeamHypothesis(length_penalty=self.length_penalty_value)
        ]

    @property
    def current(self) -> Optional[BeamHypothesis]:
        if not self._hypos:
            return None
        return self._hypos[0]

    def best(self) -> Optional[BeamHypothesis]:
        if not self._hypos:
            return None
        return max(self._hypos, key=lambda h: h.score)

    def select_k_best(
        self,
        candidates: List[BeamHypothesis],
        k: Optional[int] = None
    ) -> List[BeamHypothesis]:
        if k is None:
            k = self.num_beams
        return sorted(candidates, key=lambda h: h.score, reverse=True)[:k]

    def step(
        self,
        log_probs: np.ndarray,
        eos_token_id: int
    ) -> List[BeamHypothesis]:
        num_beams = self.num_beams
        current_hypo = self.current
        candidates: List[BeamHypothesis] = []

        top_k = min(num_beams, log_probs.shape[0])
        top_indices = np.argsort(log_probs)[-top_k:][::-1]
        top_log_probs = log_probs[top_indices]

        for i in range(top_indices.shape[0]):
            token_id = int(top_indices[i])
            log_prob = float(top_log_probs[i])
            extended = current_hypo.extend(token_id, log_prob)
            candidates.append(extended)

        next_hypos = candidates
        return next_hypos

    def step_one_vs_n(
        self,
        log_probs: np.ndarray,
        eos_token_id: int
    ) -> List[BeamHypothesis]:
        if self.current is None:
            return []
        current_hypo = self.current
        candidates: List[BeamHypothesis] = []

        num_tokens = min(self.num_beams, log_probs.shape[0])
        top_indices = np.argsort(log_probs)[-num_tokens:][::-1]

        for i in range(top_indices.shape[0]):
            token_id = int(top_indices[i])
            log_prob = float(log_probs[token_id])
            extended = current_hypo.extend(token_id, log_prob)
            candidates.append(extended)

        return candidates

    def set_hypos(self, hypos: List[BeamHypothesis]) -> None:
        self._hypos = list(hypos)

    def is_done(self, max_length: int) -> bool:
        return self.current is not None and self.current.completed(max_length)

    def detach(self, max_length: int) -> Optional[BeamHypothesis]:
        if not self._hypos:
            return None
        best = self.best()
        if best is None:
            return None
        return best


def softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    exp_x = np.exp(x - x_max)
    return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


def log_softmax(x: np.ndarray) -> np.ndarray:
    x_max = np.max(x, axis=-1, keepdims=True)
    log_sum_exp = x_max + np.log(np.sum(np.exp(x - x_max), axis=-1, keepdims=True))
    return x - log_sum_exp


@dataclass
class BeamSearchDecoder:
    num_beams: int = 4
    max_length: int = 50
    eos_token_id: int = 2
    length_penalty: float = 0.0
    beam_mode: BeamSearchMode = BeamSearchMode.BEST_K

    def __post_init__(self):
        self._beam = Beam(
            mode=self.beam_mode,
            num_beams=self.num_beams,
            length_penalty_type=LengthPenaltyType.WU,
            length_penalty_value=self.length_penalty,
        )
        self._all_hypos: List[BeamHypothesis] = []

    def decode(
        self,
        log_probs: np.ndarray,
    ) -> Optional[BeamHypothesis]:
        next_hypos = self._beam.step(log_probs, self.eos_token_id)
        self._all_hypos.extend(next_hypos)
        self._beam.set_hypos(next_hypos)
        if self._beam.is_done(self.max_length):
            return self._beam.detach(self.max_length)
        return None

    def decode_one_vs_n(
        self,
        log_probs: np.ndarray,
    ) -> Optional[BeamHypothesis]:
        next_hypos = self._beam.step_one_vs_n(log_probs, self.eos_token_id)
        self._all_hypos.extend(next_hypos)
        self._beam.set_hypos(next_hypos)
        if self._beam.is_done(self.max_length):
            return self._beam.detach(self.max_length)
        return None

    def reset(self) -> None:
        self._beam.set_hypos([
            BeamHypothesis(length_penalty=self.length_penalty)
        ])
        self._all_hypos = []

    def get_all_hypos(self) -> List[BeamHypothesis]:
        return list(self._all_hypos)

    def get_best_hypo(self) -> Optional[BeamHypothesis]:
        return self._beam.best()

    def get_top_k_hypos(self, k: int = 4) -> List[BeamHypothesis]:
        return self._beam.select_k_best(self._all_hypos, k=k)

    def force_step(
        self,
        token_id: int,
        log_prob: Optional[float] = None,
    ) -> None:
        current = self._beam.current
        if current is None:
            return
        if log_prob is None:
            log_prob = float(np.log(1.0))
        extended = current.extend(token_id, log_prob)
        self._all_hypos.append(extended)
        self._beam.set_hypos([extended])

    def length_penalty_at(self, length: int) -> float:
        return length_penalty_wu(length, alpha=self.length_penalty)
