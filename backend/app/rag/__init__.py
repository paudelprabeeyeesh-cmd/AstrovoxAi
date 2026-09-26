"""RAG package — chunking, embeddings, retrieval, parent-child, compression, citations, metadata, vector DB."""

from .chunking import Chunk, ChunkingStrategies
from .embeddings import EmbeddingGenerator, EmbeddingResult
from .retrieval import HybridRetriever, MultiQueryRetriever, RetrievalResult, BM25SparseIndex, DenseVectorIndex
from .parent_child import ChildChunk, ParentChildRetriever, ParentChildStore, ParentDocument
from .compression import ContextCompressor
from .citation import Citation, CitationEngine
from .metadata import ChunkMetadata, MetadataExtractor, MetadataFilter
from .vector_db import VectorStore, VectorRecord, SearchResult as VectorSearchResult
from .semantic_chunker import SemanticChunker
from .hybrid_retriever import HybridRetriever as AdvancedHybridRetriever

__all__ = [
    "Chunk",
    "ChunkingStrategies",
    "SemanticChunker",
    "EmbeddingGenerator",
    "EmbeddingResult",
    "HybridRetriever",
    "AdvancedHybridRetriever",
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
    "VectorStore",
    "VectorRecord",
    "VectorSearchResult",
]
