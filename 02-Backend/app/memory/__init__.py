"""
Astrovox AI Memory Architecture
Phase 3: Memory System Implementation

This module provides a structured, persistent memory system with:
- Layered memory architecture (context, conversation, semantic, episodic, procedural, workspace)
- Memory importance scoring
- Vector database integration for semantic search
- Memory retrieval and ranking engine
- Memory lifecycle management
- Workspace isolation
- Privacy controls
"""

from .context_memory import ContextMemory
from .conversation_memory import ConversationMemory
from .semantic_memory import SemanticMemory
from .episodic_memory import EpisodicMemory
from .procedural_memory import ProceduralMemory
from .workspace_memory import WorkspaceMemory
from .importance_scorer import ImportanceScorer
from .retrieval_engine import RetrievalEngine
from .vector_store import VectorStore
from .advanced_memory import AdvancedMemoryManager, MemoryFragment, ImportanceScoringEngine
from .memory_consolidation import MemoryConsolidator, ConsolidatedMemory
from .memory_ranking import MemoryRanker, RankedMemory
from .memory_manager import MemoryManager, get_memory_manager

__all__ = [
    "ContextMemory",
    "ConversationMemory",
    "SemanticMemory",
    "EpisodicMemory",
    "ProceduralMemory",
    "WorkspaceMemory",
    "ImportanceScorer",
    "RetrievalEngine",
    "VectorStore",
    "AdvancedMemoryManager",
    "MemoryFragment",
    "ImportanceScoringEngine",
    "MemoryConsolidator",
    "ConsolidatedMemory",
    "MemoryRanker",
    "RankedMemory",
    "MemoryManager",
    "get_memory_manager",
]
