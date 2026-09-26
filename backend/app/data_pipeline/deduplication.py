import logging
from dataclasses import dataclass
from typing import List, Optional
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationConfig:
    similarity_threshold: float = 0.8
    use_minhash: bool = True


class Deduplicator:
    def __init__(self, config: Optional[DeduplicationConfig] = None):
        self.config = config or DeduplicationConfig()
        self.seen_hashes = set()
        logger.info("Deduplicator initialized")

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        h = self._hash(text)
        if h in self.seen_hashes:
            return True
        self.seen_hashes.add(h)
        return False

    def deduplicate(self, documents: List[str]) -> List[str]:
        unique = []
        for doc in documents:
            if not self.is_duplicate(doc):
                unique.append(doc)
        return unique
