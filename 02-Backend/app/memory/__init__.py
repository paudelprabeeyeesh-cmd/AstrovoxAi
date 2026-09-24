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

from .context_memory import ContextMemory  # noqa: F401
from .conversation_memory import ConversationMemory  # noqa: F401
from .semantic_memory import SemanticMemory  # noqa: F401
from .episodic_memory import EpisodicMemory  # noqa: F401
from .procedural_memory import ProceduralMemory  # noqa: F401
from .workspace_memory import WorkspaceMemory  # noqa: F401
from .memory_manager import MemoryManager  # noqa: F401
from .importance_scorer import ImportanceScorer  # noqa: F401
from .retrieval_engine import RetrievalEngine  # noqa: F401
from .vector_store import VectorStore  # noqa: F401
from ..memory_service import memory_service

__all__ = [
    "ContextMemory",
    "ConversationMemory",
    "SemanticMemory",
    "EpisodicMemory",
    "ProceduralMemory",
    "WorkspaceMemory",
    "MemoryManager",
    "ImportanceScorer",
    "RetrievalEngine",
    "VectorStore",
]


class _MemoryResult:
    def __init__(self, data):
        self.id = data["id"]
        self.key = data["key"]
        self.value = data["value"]


def create_memory(user_id: str, memory_obj):
    data = memory_obj.dict() if hasattr(memory_obj, "dict") else {
        "key": getattr(memory_obj, "key", ""),
        "value": getattr(memory_obj, "value", ""),
    }
    result = memory_service.store_memory(user_id, data["key"], data["value"])
    return _MemoryResult(result)


def list_memories(user_id: str):
    from .database import get_db  # noqa: F401
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, created_at FROM memories WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [_MemoryResult(dict(r)) for r in rows]


def search_memories(user_id: str, query: str):
    results = memory_service.search_memories(user_id, query)
    return [_MemoryResult(r) for r in results]


def delete_memory(memory_id: str, user_id: str):
    from .database import get_db  # noqa: F401
    with get_db() as conn:
        conn.execute(
            "DELETE FROM memories WHERE id = ? AND user_id = ?",
            (memory_id, user_id),
        )
        conn.commit()
