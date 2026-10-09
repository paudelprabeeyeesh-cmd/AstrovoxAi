from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EncodedDescription:
    text: str
    embedding: List[float] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)


class DescriptionEncoder:
    def __init__(self, dim: int = 64):
        self.dim = dim
        self._vocab: Dict[str, int] = {}
        self._next_idx = 0

    def _get_index(self, token: str) -> int:
        if token not in self._vocab:
            self._vocab[token] = self._next_idx
            self._next_idx += 1
        return self._vocab[token]

    def _tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in text.split() if t.strip()]

    def encode(self, text: str) -> EncodedDescription:
        tokens = self._tokenize(text)
        vec = [0.0] * self.dim
        for tok in tokens:
            idx = self._get_index(tok)
            pos = idx % self.dim
            vec[pos] += 1.0
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return EncodedDescription(text=text, embedding=vec, tokens=tokens)

    def similarity(self, a: EncodedDescription, b: EncodedDescription) -> float:
        if not a.embedding or not b.embedding:
            return 0.0
        return sum(x * y for x, y in zip(a.embedding, b.embedding))

    def batch_encode(self, texts: List[str]) -> List[EncodedDescription]:
        return [self.encode(t) for t in texts]
