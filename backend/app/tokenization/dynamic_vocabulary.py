import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DynamicVocabularyConfig:
    max_vocab_size: int = 100000
    min_frequency: int = 2
    update_interval: int = 1000


class DynamicVocabulary:
    def __init__(self, config: Optional[DynamicVocabularyConfig] = None):
        self.config = config or DynamicVocabularyConfig()
        self.token_counts: dict = {}
        self.vocab: dict = {}
        logger.info("Dynamic vocabulary initialized with max size %d", self.config.max_vocab_size)

    def add_tokens(self, tokens: List[str]):
        for token in tokens:
            self.token_counts[token] = self.token_counts.get(token, 0) + 1
        self._rebuild()

    def _rebuild(self):
        sorted_tokens = sorted(self.token_counts.items(), key=lambda x: x[1], reverse=True)
        self.vocab = {token: idx for idx, (token, _) in enumerate(sorted_tokens[:self.config.max_vocab_size])}

    def encode(self, text: str) -> List[int]:
        return [self.vocab.get(token, 0) for token in text.split()]

    def size(self) -> int:
        return len(self.vocab)
