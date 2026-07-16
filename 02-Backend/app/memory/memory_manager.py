"""
Memory Manager - Phase 3 Orchestrator

Coordinates all memory layers:
- Context Memory (short-term)
- Conversation Memory
- Semantic Memory
- Episodic Memory
- Procedural Memory
- Workspace Memory

Manages the complete memory lifecycle including:
- Storage
- Retrieval
- Importance scoring
- Lifecycle management
- Compression
- Synchronization
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .context_memory import ContextMemory, ContextType
from .conversation_memory import ConversationMemory, MessageRole
from .semantic_memory import SemanticMemory, FactCategory
from .episodic_memory import EpisodicMemory, EventType
from .procedural_memory import ProceduralMemory, ProcedureStatus
from .workspace_memory import WorkspaceMemory, WorkspaceType
from .importance_scorer import ImportanceScorer
from .retrieval_engine import RetrievalEngine, RetrievalMethod
from .vector_store import VectorStore


class MemoryManager:
    """
    Central orchestrator for all memory operations.
    Coordinates between different memory layers and manages the complete memory lifecycle.
    """
    
    def __init__(self):
        # Initialize all memory layers
        self.context_memory = ContextMemory()
        self.conversation_memory = ConversationMemory()
        self.semantic_memory = SemanticMemory()
        self.episodic_memory = EpisodicMemory()
        self.procedural_memory = ProceduralMemory()
        self.workspace_memory = WorkspaceMemory()
        
        # Initialize supporting systems
        self.importance_scorer = ImportanceScorer()
        self.retrieval_engine = RetrievalEngine()
        self.vector_store = VectorStore()
        
        # Register memory stores with retrieval engine
        self._register_memory_stores()
    
    def _register_memory_stores(self):
        """Register memory stores with the retrieval engine"""
        self.retrieval_engine.register_memory_store("semantic", self.semantic_memory)
        self.retrieval_engine.register_memory_store("episodic", self.episodic_memory)
        self.retrieval_engine.register_memory_store("procedural", self.procedural_memory)
        self.retrieval_engine.register_memory_store("conversation", self.conversation_memory)
        self.retrieval_engine.register_memory_store("workspace", self.workspace_memory)
    
    # Context Memory Operations
    
    def add_context(self, key: str, value: Any, context_type: ContextType):
        """Add context information"""
        self.context_memory.add_context(key, value, context_type)
    
    def get_context(self, key: str) -> Optional[Any]:
        """Get context by key"""
        return self.context_memory.get_context(key)
    
    def get_recent_context(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent context"""
        return self.context_memory.get_all_context()
    
    # Conversation Memory Operations
    
    def create_conversation(
        self,
        user_id: int,
        title: Optional[str] = None,
    ) -> int:
        """Create a new conversation"""
        return self.conversation_memory.create_conversation(user_id, title)
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
    ) -> int:
        """Add a message to a conversation"""
        message_role = MessageRole.USER if role == "user" else MessageRole.ASSISTANT
        return self.conversation_memory.add_message(conversation_id, message_role, content)
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get messages from a conversation"""
        return self.conversation_memory.get_messages(conversation_id, limit)
    
    def get_user_conversations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all conversations for a user"""
        return self.conversation_memory.get_user_conversations(user_id)
    
    # Semantic Memory Operations
    
    def add_fact(
        self,
        fact_key: str,
        fact_value: Any,
        category: FactCategory,
        user_explicit: bool = False,
    ):
        """Add a semantic fact"""
        # Score importance
        score = self.importance_scorer.score_memory(
            content=str(fact_value),
            memory_type="semantic",
            user_explicit=user_explicit,
        )
        
        self.semantic_memory.add_fact(
            fact_key=fact_key,
            fact_value=fact_value,
            category=category,
            confidence=score,
            requires_confirmation=not user_explicit,
        )
        
        # Record repetition if this is a confirmation
        if user_explicit:
            self.semantic_memory.confirm_fact(fact_key)
    
    def get_fact(self, fact_key: str) -> Optional[Any]:
        """Get a semantic fact"""
        return self.semantic_memory.get_fact(fact_key)
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get all user preferences"""
        return self.semantic_memory.get_all_preferences()
    
    # Episodic Memory Operations
    
    def add_event(
        self,
        user_id: int,
        event_type: EventType,
        title: str,
        description: str,
        significance: float = 0.5,
        related_project: Optional[str] = None,
    ) -> str:
        """Add an episodic event"""
        return self.episodic_memory.add_event(
            user_id=user_id,
            event_type=event_type,
            title=title,
            description=description,
            significance=significance,
            related_project=related_project,
        )
    
    def get_user_events(self, user_id: int) -> List[Dict[str, Any]]:
        """Get events for a user"""
        return self.episodic_memory.get_user_events(user_id)
    
    # Procedural Memory Operations
    
    def create_procedure(
        self,
        name: str,
        description: str,
        steps: List[Any],
        category: str = "general",
    ) -> str:
        """Create a new procedure"""
        return self.procedural_memory.create_procedure(
            name=name,
            description=description,
            steps=steps,
            category=category,
        )
    
    def get_procedures(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get procedures, optionally filtered by category"""
        if category:
            return self.procedural_memory.get_procedures_by_category(category)
        return self.procedural_memory.get_all_procedures()
    
    # Workspace Memory Operations
    
    def create_workspace(
        self,
        user_id: int,
        name: str,
        workspace_type: WorkspaceType,
        description: Optional[str] = None,
    ) -> str:
        """Create a new workspace"""
        return self.workspace_memory.create_workspace(
            user_id=user_id,
            name=name,
            workspace_type=workspace_type,
            description=description,
        )
    
    def get_user_workspaces(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all workspaces for a user"""
        return self.workspace_memory.get_user_workspaces(user_id)
    
    def add_workspace_note(
        self,
        workspace_id: str,
        note: str,
        title: Optional[str] = None,
    ):
        """Add a note to a workspace"""
        self.workspace_memory.add_note(workspace_id, note, title)
    
    def get_workspace_notes(self, workspace_id: str) -> List[Dict[str, Any]]:
        """Get notes from a workspace"""
        return self.workspace_memory.get_notes(workspace_id)
    
    # Unified Retrieval Operations
    
    async def retrieve_relevant_memory(
        self,
        query: str,
        user_id: int,
        workspace_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories across all layers.
        
        Args:
            query: Search query
            user_id: User ID
            workspace_id: Optional workspace filter
            limit: Maximum results
        
        Returns:
            List of relevant memories
        """
        matches = await self.retrieval_engine.retrieve(
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            method=RetrievalMethod.HYBRID,
            limit=limit,
        )
        
        return [match.to_dict() for match in matches]
    
    def assemble_context_for_request(
        self,
        user_id: int,
        query: str,
        workspace_id: Optional[str] = None,
    ) -> str:
        """
        Assemble relevant context for a request.
        
        Args:
            user_id: User ID
            query: User's query
            workspace_id: Optional workspace ID
        
        Returns:
            Assembled context string
        """
        # Get recent context
        context = self.context_memory.get_all_context()
        
        # Retrieve relevant memories
        import asyncio
        matches = asyncio.run(self.retrieve_relevant_memory(
            query=query,
            user_id=user_id,
            workspace_id=workspace_id,
            limit=5,
        ))
        
        # Assemble context
        context_parts = []
        
        # Add context memory
        if context:
            context_parts.append("Current Context:")
            for key, value in context.items():
                context_parts.append(f"  {key}: {value}")
        
        # Add relevant memories
        if matches:
            context_parts.append("\nRelevant Memories:")
            for match in matches:
                context_parts.append(f"  [{match['memory_type']}] {match['content'][:200]}")
        
        return "\n".join(context_parts)
    
    # Memory Lifecycle Operations
    
    def score_memory_importance(
        self,
        content: str,
        memory_type: str,
        user_explicit: bool = False,
    ) -> float:
        """Calculate importance score for a memory"""
        return self.importance_scorer.score_memory(
            content=content,
            memory_type=memory_type,
            user_explicit=user_explicit,
        )
    
    def should_retain_memory(
        self,
        score: float,
        memory_type: str,
        age_days: int = 0,
    ) -> bool:
        """Determine if a memory should be retained"""
        return self.importance_scorer.should_retain(score, memory_type, age_days)
    
    def get_storage_recommendation(
        self,
        content: str,
        memory_type: str,
        current_score: float,
        age_days: int = 0,
    ) -> Dict[str, Any]:
        """Get storage recommendation for a memory"""
        return self.importance_scorer.get_storage_recommendation(
            content=content,
            memory_type=memory_type,
            current_score=current_score,
            age_days=age_days,
        )
    
    # Vector Store Operations
    
    def add_embedding(
        self,
        memory_id: str,
        embedding: Any,
        memory_type: str,
        workspace_id: Optional[str] = None,
    ):
        """Add an embedding to the vector store"""
        import numpy as np
        if isinstance(embedding, list):
            embedding = np.array(embedding)
        
        self.vector_store.add_embedding(
            memory_id=memory_id,
            embedding=embedding,
            metadata={
                "memory_type": memory_type,
                "workspace_id": workspace_id,
            },
        )
    
    def similarity_search(
        self,
        query_embedding: Any,
        top_k: int = 10,
        memory_type: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """Search for similar memories using embeddings"""
        import numpy as np
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding)
        
        return self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            memory_type=memory_type,
        )
    
    # Statistics and Summary
    
    def get_memory_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a comprehensive summary of all memory layers"""
        return {
            "context": self.context_memory.get_context_summary(),
            "conversations": {
                "total": len(self.conversation_memory.get_user_conversations(user_id)),
            },
            "semantic": self.semantic_memory.get_summary(),
            "episodic": self.episodic_memory.get_summary(user_id),
            "procedural": self.procedural_memory.get_summary(),
            "workspaces": {
                "total": len(self.workspace_memory.get_user_workspaces(user_id)),
            },
            "retrieval": self.retrieval_engine.get_retrieval_stats(),
            "vector_store": self.vector_store.get_stats(),
        }
    
    def cleanup_expired_context(self):
        """Clean up expired context memory"""
        self.context_memory._cleanup_expired()
    
    def clear_retrieval_cache(self):
        """Clear the retrieval cache"""
        self.retrieval_engine.clear_cache()
