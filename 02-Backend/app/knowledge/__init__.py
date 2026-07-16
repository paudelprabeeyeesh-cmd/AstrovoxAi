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

from .ingestion_pipeline import IngestionPipeline, IngestionStage
from .document_processor import DocumentProcessor
from .chunking_strategy import ChunkingStrategy
from .metadata_system import MetadataSystem
from .hybrid_retrieval import HybridRetrieval
from .citation_system import CitationSystem
from .knowledge_packs import KnowledgePackManager

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
