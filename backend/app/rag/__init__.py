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
from .graph_rag import GraphRAG, GraphNode, GraphEdge
from .knowledge_graph import KnowledgeGraph, KnowledgeTriple
from .incremental_indexing import IncrementalIndexer, IndexedDocument
from .hallucination_detection import HallucinationDetector, HallucinationResult
from .long_context import LongContextOptimizer, ContextWindow
from .multimodal_rag import MultiModalRAG, MultiModalChunk
from .live_sync import LiveDocumentSync, SyncEvent
from .citation_verification import CitationVerifier, VerifiedCitation
from .cross_document import CrossDocumentReasoner, DocumentRelation
from .reranker import Reranker, RerankResult
from .adaptive_chunking import AdaptiveChunk, AdaptiveChunker

__all__ = [
    "Chunk",
    "ChunkingStrategies",
    "SemanticChunker",
    "AdaptiveChunk",
    "AdaptiveChunker",
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
    "CitationVerifier",
    "VerifiedCitation",
    "ChunkMetadata",
    "MetadataExtractor",
    "MetadataFilter",
    "VectorStore",
    "VectorRecord",
    "VectorSearchResult",
    "GraphRAG",
    "GraphNode",
    "GraphEdge",
    "KnowledgeGraph",
    "KnowledgeTriple",
    "IncrementalIndexer",
    "IndexedDocument",
    "HallucinationDetector",
    "HallucinationResult",
    "LongContextOptimizer",
    "ContextWindow",
    "MultiModalRAG",
    "MultiModalChunk",
    "LiveDocumentSync",
    "SyncEvent",
    "CrossDocumentReasoner",
    "DocumentRelation",
    "Reranker",
    "RerankResult",
]
