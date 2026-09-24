from typing import Dict, List, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class Signal:
    sender: str
    receiver: str
    content: np.ndarray
    meaning: str
    strength: float = 1.0
    timestamp: int = 0


class EmergentCommunication:
    def __init__(self, vocab_size: int = 64, signal_dim: int = 8):
        self.vocab_size = vocab_size
        self.signal_dim = signal_dim
        self.vocabulary: Dict[int, str] = {}
        self.reverse_vocab: Dict[str, int] = {}
        self.signal_history: List[Signal] = []
        self.communication_stats: Dict[str, int] = {}
        self._step = 0
        self._vocab_counter = 0

    def send(self, sender: str, receiver: str, content: np.ndarray, meaning: str) -> Signal:
        token = self._encode(content)
        self._update_vocabulary(token, meaning)
        signal = Signal(
            sender=sender,
            receiver=receiver,
            content=content.copy(),
            meaning=meaning,
            strength=float(np.linalg.norm(content)),
            timestamp=self._step,
        )
        self.signal_history.append(signal)
        key = f"{sender}->{receiver}"
        self.communication_stats[key] = self.communication_stats.get(key, 0) + 1
        if len(self.signal_history) > 1000:
            self.signal_history.pop(0)
        self._step += 1
        return signal

    def receive(self, signal: Signal) -> Dict[str, Any]:
        decoded = self._decode(signal.content)
        return {
            "sender": signal.sender,
            "meaning": decoded,
            "original_meaning": signal.meaning,
            "strength": signal.strength,
            "match": decoded == signal.meaning,
        }

    def language_emergence_metric(self) -> float:
        if not self.signal_history:
            return 0.0
        matches = sum(1 for s in self.signal_history if self._decode(s.content) == s.meaning)
        return matches / max(len(self.signal_history), 1)

    def negotiate_protocol(self, agent_a: str, agent_b: str, shared_tasks: List[str]) -> Dict[str, str]:
        protocol = {}
        for task in shared_tasks:
            token = hash(f"{agent_a}:{agent_b}:{task}") % self.vocab_size
            protocol[task] = str(token)
        return protocol

    def _encode(self, content: np.ndarray) -> int:
        if content.size == 0:
            return 0
        discrete = np.clip(np.floor(content * self.vocab_size), 0, self.vocab_size - 1)
        token = int(np.sum(discrete.astype(np.int64)) % self.vocab_size)
        return token

    def _decode(self, content: np.ndarray) -> str:
        token = self._encode(content)
        return self.vocabulary.get(token, f"token_{token}")

    def _update_vocabulary(self, token: int, meaning: str) -> None:
        if token not in self.vocabulary:
            self._vocab_counter += 1
            self.vocabulary[token] = meaning
            self.reverse_vocab[meaning] = token
