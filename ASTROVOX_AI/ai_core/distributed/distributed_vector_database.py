from typing import Optional, Dict, Any, List, Tuple
import numpy as np


class DistributedVectorDatabase:
    def __init__(self, num_shards: int, embedding_dim: int = 768):
        self.num_shards = num_shards
        self.embedding_dim = embedding_dim
        self.shards: List[Dict[str, Any]] = [{'vectors': [], 'metadata': []} for _ in range(num_shards)]
        self.index_type = 'flat'

    def add_document(self, shard_id: int, document: Dict[str, str], embedding: Optional[np.ndarray] = None) -> None:
        if embedding is None:
            embedding = np.random.randn(self.embedding_dim).astype(np.float32)
        self.shards[shard_id]['vectors'].append(embedding)
        self.shards[shard_id]['metadata'].append(document)

    def search(self, query_embedding: np.ndarray, top_k: int = 10, shard_ids: Optional[List[int]] = None) -> List[Tuple[float, Dict[str, str]]]:
        shard_ids = shard_ids or list(range(self.num_shards))
        results = []
        for shard_id in shard_ids:
            vectors = np.array(self.shards[shard_id]['vectors'])
            if len(vectors) == 0:
                continue
            scores = np.dot(vectors, query_embedding)
            top_indices = np.argsort(scores)[::-1][:top_k]
            for idx in top_indices:
                results.append((float(scores[idx]), self.shards[shard_id]['metadata'][idx]))
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    def add_batch(self, shard_id: int, documents: List[Dict[str, str]], embeddings: Optional[np.ndarray] = None) -> None:
        for i, doc in enumerate(documents):
            emb = embeddings[i] if embeddings is not None and i < len(embeddings) else None
            self.add_document(shard_id, doc, emb)

    def clear(self) -> None:
        for shard in self.shards:
            shard['vectors'].clear()
            shard['metadata'].clear()
