from typing import Dict, Any, List
from ASTROVOX_AI.ai_core.rag.hybrid_rag import HybridRAG
from ASTROVOX_AI.ai_core.distributed.distributed_vector_database import DistributedVectorDatabase


class MultiNodeRAG:
    def __init__(self, num_nodes: int, embedding_dim: int = 768):
        self.num_nodes = num_nodes
        self.nodes: List[HybridRAG] = [HybridRAG() for _ in range(num_nodes)]
        self.vector_db = DistributedVectorDatabase(num_nodes, embedding_dim)

    def distributed_retrieve(self, query: str, top_k: int = 10, use_graph: bool = False) -> List[Dict[str, Any]]:
        results = []
        for i, node in enumerate(self.nodes):
            node_results = node.retrieve(query, top_k=top_k, use_graph=use_graph)
            results.extend(node_results)
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:top_k]

    def distributed_index(self, documents: List[Dict[str, str]]) -> None:
        for i, doc in enumerate(documents):
            node_id = i % self.num_nodes
            self.nodes[node_id].index_document(doc)
            self.vector_db.add_document(node_id, doc)

    def clear(self) -> None:
        for node in self.nodes:
            node.clear()
        self.vector_db.clear()
