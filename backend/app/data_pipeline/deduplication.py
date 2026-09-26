import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from .minhash_lsh import LSH, MinHash

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationConfig:
    similarity_threshold: float = 0.8
    use_minhash: bool = True
    minhash_num_hashes: int = 128
    minhash_num_bands: int = 16


class Deduplicator:
    def __init__(self, config: Optional[DeduplicationConfig] = None):
        self.config = config or DeduplicationConfig()
        self.seen_hashes: set = set()
        self.minhash = MinHash(
            MinHashConfig(
                num_hashes=self.config.minhash_num_hashes,
                num_bands=self.config.minhash_num_bands,
                bands_rows=self.config.minhash_num_hashes // self.config.minhash_num_bands,
            )
        )
        self.lsh = LSH(
            MinHashConfig(
                num_hashes=self.config.minhash_num_hashes,
                num_bands=self.config.minhash_num_bands,
                bands_rows=self.config.minhash_num_hashes // self.config.minhash_num_bands,
            )
        )
        self.doc_signatures: Dict[int, List[int]] = {}
        logger.info(
            "Deduplicator initialized: threshold=%.2f, minhash=%s",
            self.config.similarity_threshold,
            self.config.use_minhash,
        )

    def _tokenize(self, text: str) -> List[str]:
        words = text.lower().split()
        return words

    def _hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        h = self._hash(text)
        if h in self.seen_hashes:
            return True
        if self.config.use_minhash:
            tokens = self._tokenize(text)
            sig = self.minhash.signature(tokens)
            candidates = self.lsh.query(sig)
            for doc_id in candidates:
                existing_sig = self.doc_signatures[doc_id]
                jaccard = self.minhash.jaccard(sig, existing_sig)
                if jaccard >= self.config.similarity_threshold:
                    self.seen_hashes.add(h)
                    return True
            doc_id = len(self.doc_signatures)
            self.doc_signatures[doc_id] = sig
            self.lsh.index(str(doc_id), sig)
        self.seen_hashes.add(h)
        return False

    def deduplicate(self, documents: List[str]) -> List[str]:
        unique = []
        for doc in documents:
            if not self.is_duplicate(doc):
                unique.append(doc)
        return unique
