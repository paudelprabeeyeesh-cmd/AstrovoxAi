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
]
