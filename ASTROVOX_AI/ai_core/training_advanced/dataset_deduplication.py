from typing import List, Dict, Tuple
import hashlib
from ASTROVOX_AI.ai_core.rag.incremental_indexing import IncrementalIndexer


class DatasetDeduplicator:
    def __init__(self, hash_method: str = 'sha256'):
        self.hash_method = hash_method
        self.seen_hashes: set = set()
        self.indexer = IncrementalIndexer(deduplicate=True)
        self.stats = {'total': 0, 'unique': 0, 'duplicates': 0}

    def compute_hash(self, text: str) -> str:
        if self.hash_method == 'sha256':
            return hashlib.sha256(text.encode('utf-8')).hexdigest()
        elif self.hash_method == 'md5':
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        return str(hash(text))

    def deduplicate(self, documents: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        unique = []
        duplicates = []
        for doc in documents:
            text = doc.get('text', '')
            doc_hash = self.compute_hash(text)
            self.stats['total'] += 1
            if doc_hash not in self.seen_hashes:
                self.seen_hashes.add(doc_hash)
                unique.append(doc)
                self.stats['unique'] += 1
            else:
                duplicates.append(doc)
                self.stats['duplicates'] += 1
        return unique, duplicates

    def get_stats(self) -> Dict[str, int]:
        return self.stats.copy()
