from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import hashlib


class IncrementalIndexer:
    def __init__(self, batch_size: int = 100, deduplicate: bool = True):
        self.batch_size = batch_size
        self.deduplicate = deduplicate
        self.document_store: Dict[str, Dict[str, Any]] = {}
        self.seen_hashes: set = set()
        self.last_indexed: Optional[datetime] = None

    def compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def add_documents(self, documents: List[Dict[str, str]]) -> Tuple[int, int]:
        new_docs = 0
        skipped = 0
        for doc in documents:
            text = doc.get('text', '')
            doc_hash = self.compute_hash(text)
            if self.deduplicate and doc_hash in self.seen_hashes:
                skipped += 1
                continue
            doc_id = doc.get('id', str(len(self.document_store)))
            self.document_store[doc_id] = {'text': text, 'hash': doc_hash, 'indexed_at': datetime.now().isoformat(), 'metadata': doc.get('metadata', {})}
            self.seen_hashes.add(doc_hash)
            new_docs += 1
        self.last_indexed = datetime.now()
        return new_docs, skipped

    def delete_document(self, doc_id: str) -> bool:
        if doc_id in self.document_store:
            del self.document_store[doc_id]
            return True
        return False

    def get_stats(self) -> Dict[str, int]:
        return {'total_documents': len(self.document_store), 'total_hashes': len(self.seen_hashes)}

    def get_documents(self) -> List[Dict[str, Any]]:
        return list(self.document_store.values())
