import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MultilingualTokenizerConfig:
    vocab_size: int = 100000
    languages: List[str] = None

    def __post_init__(self):
        if self.languages is None:
            self.languages = ["en", "es", "fr", "de", "zh", "ja", "ko", "ar", "hi", "ru"]


class MultilingualTokenizer:
    def __init__(self, config: Optional[MultilingualTokenizerConfig] = None):
        self.config = config or MultilingualTokenizerConfig()
        logger.info("Multilingual tokenizer initialized for %d languages", len(self.config.languages))

    def tokenize(self, text: str, language: str = "en") -> List[str]:
        return text.split()

    def encode(self, text: str, language: str = "en") -> List[int]:
        return [hash(token) % self.config.vocab_size for token in self.tokenize(text, language)]
