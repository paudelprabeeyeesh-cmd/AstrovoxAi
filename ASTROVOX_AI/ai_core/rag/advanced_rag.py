"""
Advanced RAG with hybrid retrieval, knowledge graphs, and multi-vector indexing.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class HybridRAGRetriever:
    def __init__(self, vector_store: Any, keyword_store: Any, alpha: float = 0.5):
        self.vector_store = vector_store
        self.keyword_store = keyword_store
        self.alpha = alpha

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        dense_results = self.vector_store.search(query, top_k=top_k)
        sparse_results = self.keyword_store.search(query, top_k=top_k)
        combined = self._reciprocal_rank_fusion(dense_results, sparse_results)
        return combined[:top_k]

    def _reciprocal_rank_fusion(self, dense: List[Dict], sparse: List[Dict], k: int = 60) -> List[Dict]:
        scores: Dict[str, float] = {}
        for i, doc in enumerate(dense):
            doc_id = doc.get('id', str(i))
            scores[doc_id] = scores.get(doc_id, 0.0) + self.alpha * (1.0 / (k + i + 1))
        for i, doc in enumerate(sparse):
            doc_id = doc.get('id', str(i))
            scores[doc_id] = scores.get(doc_id, 0.0) + (1 - self.alpha) * (1.0 / (k + i + 1))
        return sorted(dense + sparse, key=lambda x: scores.get(x.get('id', ''), 0.0), reverse=True)


class KnowledgeGraphRetriever:
    def __init__(self, graph_db: Any, embedding_model: nn.Module):
        self.graph_db = graph_db
        self.embedding_model = embedding_model

    def retrieve(self, query: str, depth: int = 2, top_k: int = 10) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model(query)
        initial_nodes = self.graph_db.search_by_embedding(query_embedding, top_k=top_k)
        expanded = []
        for node in initial_nodes:
            neighbors = self.graph_db.get_neighbors(node['id'], depth=depth)
            expanded.extend(neighbors)
        return expanded[:top_k]

    def path_query(self, start_entity: str, end_entity: str, max_hops: int = 3) -> List[List[str]]:
        paths = []
        visited = {start_entity}
        self._dfs_paths(start_entity, end_entity, max_hops, [start_entity], paths, visited)
        return paths

    def _dfs_paths(self, current: str, end: str, max_hops: int, path: List[str], paths: List[List[str]], visited: set) -> None:
        if len(path) > max_hops:
            return
        if current == end:
            paths.append(path.copy())
            return
        neighbors = self.graph_db.get_neighbors(current)
        for neighbor in neighbors:
            if neighbor['id'] not in visited:
                visited.add(neighbor['id'])
                path.append(neighbor['id'])
                self._dfs_paths(neighbor['id'], end, max_hops, path, paths, visited)
                path.pop()
                visited.remove(neighbor['id'])


class Reranker:
    def __init__(self, cross_encoder: nn.Module, device: Optional[torch.device] = None):
        self.cross_encoder = cross_encoder
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[int, float]]:
        pairs = [(query, doc) for doc in documents]
        with torch.no_grad():
            scores = self.cross_encoder(pairs)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
