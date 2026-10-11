"""RAG services package.

Re-exports the retrieval implementations so callers can use either the
package (`from app.services.rag import ...`) or a submodule. The class was
renamed during a refactor: `RAGEngine` in ``rag_engine`` is the newer
implementation, and ``RAGService`` in the sibling module stays available as
the historical name.
"""

from .graph_rag import Chunk, Graph, GraphRAG
from .graph_rag_v2 import GraphRAGV2
from .rag_engine import RAGEngine
from .service import RAGService

__all__ = [
    "RAGEngine",
    "RAGService",
    "GraphRAG",
    "GraphRAGV2",
    "Chunk",
    "Graph",
]
