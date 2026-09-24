"""
Astrovox AI Knowledge & RAG Platform
Phase 5: Knowledge & Retrieval System Implementation

This module provides a comprehensive knowledge engine for:
- Document ingestion and processing
- Vector search and semantic retrieval
- Hybrid retrieval (keyword + semantic)
- Citation and traceability
- Knowledge workspace isolation
- Domain knowledge packs
- Knowledge graph layer
- Multi-level summarization
- External connectors
- Knowledge updating and versioning
"""

from .ingestion_pipeline import IngestionPipeline, IngestionStage  # noqa: F401
from .document_processor import DocumentProcessor  # noqa: F401
from .chunking_strategy import ChunkingStrategy  # noqa: F401
from .metadata_system import MetadataSystem  # noqa: F401
from .hybrid_retrieval import HybridRetrieval  # noqa: F401
from .citation_system import CitationSystem  # noqa: F401
from .knowledge_packs import KnowledgePackManager  # noqa: F401

__all__ = [
    "IngestionPipeline",
    "IngestionStage",
    "DocumentProcessor",
    "ChunkingStrategy",
    "MetadataSystem",
    "HybridRetrieval",
    "CitationSystem",
    "KnowledgePackManager",
]
