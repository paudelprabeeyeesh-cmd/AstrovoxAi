<<<<<<< HEAD
"""RAG package — chunking, embeddings, retrieval, parent-child, compression, citations, metadata."""

from .chunking import Chunk, ChunkingStrategies
from .embeddings import EmbeddingGenerator, EmbeddingResult
from .retrieval import HybridRetriever, MultiQueryRetriever, RetrievalResult, BM25SparseIndex, DenseVectorIndex
from .parent_child import ChildChunk, ParentChildRetriever, ParentChildStore, ParentDocument
from .compression import ContextCompressor
from .citation import Citation, CitationEngine
from .metadata import ChunkMetadata, MetadataExtractor, MetadataFilter

__all__ = [
    "Chunk",
    "ChunkingStrategies",
    "EmbeddingGenerator",
    "EmbeddingResult",
    "HybridRetriever",
    "MultiQueryRetriever",
    "RetrievalResult",
    "BM25SparseIndex",
    "DenseVectorIndex",
    "ChildChunk",
    "ParentChildRetriever",
    "ParentChildStore",
    "ParentDocument",
    "ContextCompressor",
    "Citation",
    "CitationEngine",
    "ChunkMetadata",
    "MetadataExtractor",
    "MetadataFilter",
=======
"""
RAG package for document ingestion, embedding storage, and retrieval.
"""

from .pipeline import RAGPipeline, DocumentIngestionResult
from .embedding_store import EmbeddingStore, StoredEmbedding
from .retriever import RAGRetriever, RetrievalResult, BM25Retriever

__all__ = [
    "RAGPipeline",
    "DocumentIngestionResult",
    "EmbeddingStore",
    "StoredEmbedding",
    "RAGRetriever",
    "RetrievalResult",
    "BM25Retriever",
>>>>>>> 10617909505295e4a37b817bb54db2364934b978
]
