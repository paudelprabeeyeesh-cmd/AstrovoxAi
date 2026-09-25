from typing import Optional, List, Dict, Any, Tuple
import torch
import torch.nn as nn
import torch.nn.functional as F
from ASTROVOX_AI.ai_core.distributed.distributed_vector_database import DistributedVectorDatabase
from ASTROVOX_AI.ai_core.rag.graph_rag import GraphRAG


class HybridRAG:
    def __init__(self, embedding_dim: int = 768, vector_db: Optional[DistributedVectorDatabase] = None, graph_rag: Optional[GraphRAG] = None):
        self.embedding_dim = embedding_dim
        self.vector_db = vector_db or DistributedVectorDatabase(num_shards=4, embedding_dim=embedding_dim)
        self.graph_rag = graph_rag or GraphRAG()
        self.documents: Dict[str, Dict[str, str]] = {}
        self.embeddings: Dict[str, torch.Tensor] = {}

    def index_document(self, doc_id: str, text: str, metadata: Optional[Dict[str, str]] = None) -> None:
        self.documents[doc_id] = {'text': text, 'metadata': metadata or {}}
        embedding = torch.randn(self.embedding_dim)
        self.embeddings[doc_id] = embedding
        shard_id = hash(doc_id) % self.vector_db.num_shards
        self.vector_db.add_document(shard_id, self.documents[doc_id], embedding.numpy())

    def retrieve(self, query: str, top_k: int = 5, use_graph: bool = False, alpha: float = 0.7) -> List[Dict[str, Any]]:
        query_embedding = torch.randn(self.embedding_dim)
        vector_results = self.vector_db.search(query_embedding.numpy(), top_k=top_k * 2)
        vector_docs = []
        for score, doc in vector_results:
            vector_docs.append({**doc, 'score': score * alpha, 'source': 'vector'})
        if use_graph:
            graph_results = self.graph_rag.retrieve(query, top_k=top_k * 2)
            graph_docs = [{**doc, 'score': doc.get('score', 0.0) * (1 - alpha), 'source': 'graph'} for doc in graph_results]
            combined = vector_docs + graph_docs
        else:
            combined = vector_docs
        combined.sort(key=lambda x: x.get('score', 0), reverse=True)
        return combined[:top_k]

    def batch_index(self, documents: List[Dict[str, str]]) -> None:
        for doc in documents:
            doc_id = doc.get('id', str(len(self.documents)))
            self.index_document(doc_id, doc.get('text', ''), doc.get('metadata'))
