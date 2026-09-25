"""
Memory Retrieval & Ranking Engine - Phase 3.5

Retrieval pipeline:
- User Request
- Intent Detection
- Workspace Filter
- Semantic Search
- Relevance Ranking
- Context Assembly
- AI Response

The AI should retrieve only the most relevant memories to avoid unnecessary context.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import re


class RetrievalMethod(Enum):
    """Methods for memory retrieval"""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    METADATA = "metadata"


class MemoryMatch:
    """Represents a memory match with relevance score"""
    
    def __init__(
        self,
        memory_id: str,
        content: str,
        memory_type: str,
        relevance_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.memory_id = memory_id
        self.content = content
        self.memory_type = memory_type
        self.relevance_score = relevance_score
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata,
        }


class RetrievalEngine:
    """
    Retrieves and ranks memories based on relevance to the current request.
    Implements the retrieval pipeline to provide the most relevant context.
    """
    
    def __init__(self):
        self.memory_stores: Dict[str, Any] = {}
        self.retrieval_cache: Dict[str, List[MemoryMatch]] = {}
        self.cache_ttl = 300  # 5 minutes
    
    def register_memory_store(self, memory_type: str, store: Any):
        """Register a memory store for a specific type"""
        self.memory_stores[memory_type] = store
    
    async def retrieve(
        self,
        query: str,
        user_id: int,
        workspace_id: Optional[str] = None,
        memory_types: Optional[List[str]] = None,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
        limit: int = 10,
        min_relevance: float = 0.3,
    ) -> List[MemoryMatch]:
        """
        Retrieve relevant memories for a query.
        
        Args:
            query: Search query
            user_id: User ID
            workspace_id: Optional workspace filter
            memory_types: Optional memory type filter
            method: Retrieval method
            limit: Maximum number of results
            min_relevance: Minimum relevance threshold
        
        Returns:
            List of ranked memory matches
        """
        # Check cache first
        cache_key = self._generate_cache_key(query, user_id, workspace_id, memory_types)
        if cache_key in self.retrieval_cache:
            cached_results = self.retrieval_cache[cache_key]
            if self._is_cache_valid(cache_key):
                return cached_results[:limit]
        
        # Retrieve from memory stores
        all_matches = []
        
        types_to_search = memory_types or list(self.memory_stores.keys())
        
        for memory_type in types_to_search:
            if memory_type not in self.memory_stores:
                continue
            
            store = self.memory_stores[memory_type]
            matches = await self._retrieve_from_store(
                store,
                query,
                user_id,
                workspace_id,
                memory_type,
                method,
            )
            all_matches.extend(matches)
        
        # Rank by relevance
        ranked_matches = self._rank_matches(all_matches, query)
        
        # Filter by minimum relevance
        ranked_matches = [
            match for match in ranked_matches
            if match.relevance_score >= min_relevance
        ]
        
        # Cache results
        self.retrieval_cache[cache_key] = ranked_matches
        self._set_cache_timestamp(cache_key)
        
        return ranked_matches[:limit]
    
    async def _retrieve_from_store(
        self,
        store: Any,
        query: str,
        user_id: int,
        workspace_id: Optional[str],
        memory_type: str,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve memories from a specific store"""
        matches = []
        
        try:
            # Different retrieval strategies based on memory type
            if memory_type == "semantic":
                matches = self._retrieve_semantic(store, query, user_id, method)
            elif memory_type == "episodic":
                matches = self._retrieve_episodic(store, query, user_id, method)
            elif memory_type == "procedural":
                matches = self._retrieve_procedural(store, query, method)
            elif memory_type == "conversation":
                matches = self._retrieve_conversation(store, query, user_id, method)
            elif memory_type == "workspace":
                matches = self._retrieve_workspace(store, query, workspace_id, method)
            else:
                # Generic retrieval
                matches = self._retrieve_generic(store, query, method)
        
        except Exception as e:
            # Log error but continue with other stores
            print(f"Error retrieving from {memory_type}: {e}")
        
        return matches
    
    def _retrieve_semantic(
        self,
        store: Any,
        query: str,
        user_id: int,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve from semantic memory"""
        matches = []
        
        # Get all facts
        facts = store.get_facts_by_category(store.FactCategory.PREFERENCE)
        
        query_lower = query.lower()
        
        for key, value in facts.items():
            # Keyword matching
            if method in [RetrievalMethod.KEYWORD, RetrievalMethod.HYBRID]:
                if query_lower in key.lower() or (isinstance(value, str) and query_lower in value.lower()):
                    relevance = self._calculate_keyword_relevance(query, str(value))
                    matches.append(MemoryMatch(
                        memory_id=key,
                        content=str(value),
                        memory_type="semantic",
                        relevance_score=relevance,
                    ))
        
        return matches
    
    def _retrieve_episodic(
        self,
        store: Any,
        query: str,
        user_id: int,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve from episodic memory"""
        matches = []
        
        events = store.get_user_events(user_id)
        query_lower = query.lower()
        
        for event in events:
            # Search in title and description
            text = f"{event['title']} {event['description']}"
            
            if method in [RetrievalMethod.KEYWORD, RetrievalMethod.HYBRID]:
                if query_lower in text.lower():
                    relevance = self._calculate_keyword_relevance(query, text)
                    matches.append(MemoryMatch(
                        memory_id=event['event_id'],
                        content=event['description'],
                        memory_type="episodic",
                        relevance_score=relevance * event.get('significance', 0.5),
                        metadata={"event_type": event['event_type']},
                    ))
        
        return matches
    
    def _retrieve_procedural(
        self,
        store: Any,
        query: str,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve from procedural memory"""
        matches = []
        
        procedures = store.get_all_procedures()
        query_lower = query.lower()
        
        for proc in procedures:
            text = f"{proc['name']} {proc['description']}"
            
            if method in [RetrievalMethod.KEYWORD, RetrievalMethod.HYBRID]:
                if query_lower in text.lower():
                    relevance = self._calculate_keyword_relevance(query, text)
                    matches.append(MemoryMatch(
                        memory_id=proc['procedure_id'],
                        content=proc['description'],
                        memory_type="procedural",
                        relevance_score=relevance,
                        metadata={"category": proc['category']},
                    ))
        
        return matches
    
    def _retrieve_conversation(
        self,
        store: Any,
        query: str,
        user_id: int,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve from conversation memory"""
        matches = []
        
        conversations = store.get_user_conversations(user_id, limit=20)
        query_lower = query.lower()
        
        for conv in conversations:
            # Search in title
            if query_lower in conv['title'].lower():
                relevance = self._calculate_keyword_relevance(query, conv['title'])
                matches.append(MemoryMatch(
                    memory_id=str(conv['conversation_id']),
                    content=conv['title'],
                    memory_type="conversation",
                    relevance_score=relevance * 0.7,
                    metadata={"conversation_id": conv['conversation_id']},
                ))
        
        return matches
    
    def _retrieve_workspace(
        self,
        store: Any,
        query: str,
        workspace_id: Optional[str],
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Retrieve from workspace memory"""
        matches = []
        
        if not workspace_id:
            return matches
        
        search_results = store.search_workspace(workspace_id, query)
        query_lower = query.lower()
        
        # Search in notes
        for note in search_results.get('notes', []):
            text = f"{note['title']} {note['content']}"
            relevance = self._calculate_keyword_relevance(query, text)
            matches.append(MemoryMatch(
                memory_id=f"note_{note['note_id']}",
                content=note['content'],
                memory_type="workspace",
                relevance_score=relevance,
                metadata={"type": "note", "workspace_id": workspace_id},
            ))
        
        # Search in tasks
        for task in search_results.get('tasks', []):
            relevance = self._calculate_keyword_relevance(query, task['task'])
            matches.append(MemoryMatch(
                memory_id=f"task_{task['task_id']}",
                content=task['task'],
                memory_type="workspace",
                relevance_score=relevance,
                metadata={"type": "task", "workspace_id": workspace_id},
            ))
        
        return matches
    
    def _retrieve_generic(
        self,
        store: Any,
        query: str,
        method: RetrievalMethod,
    ) -> List[MemoryMatch]:
        """Generic retrieval for unknown store types"""
        # Try to call a search method if available
        if hasattr(store, 'search'):
            try:
                results = store.search(query)
                return [
                    MemoryMatch(
                        memory_id=str(result.get('id', '')),
                        content=str(result.get('content', '')),
                        memory_type="generic",
                        relevance_score=0.5,
                    )
                    for result in results
                ]
            except:
                pass
        
        return []
    
    def _calculate_keyword_relevance(self, query: str, content: str) -> float:
        """Calculate relevance based on keyword matching"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Exact phrase match
        if query_lower in content_lower:
            return 1.0
        
        # Word overlap
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        overlap = query_words & content_words
        overlap_ratio = len(overlap) / len(query_words)
        
        return overlap_ratio
    
    def _rank_matches(self, matches: List[MemoryMatch], query: str) -> List[MemoryMatch]:
        """Rank matches by relevance score"""
        # Sort by relevance score (descending)
        matches.sort(key=lambda m: m.relevance_score, reverse=True)
        return matches
    
    def _generate_cache_key(
        self,
        query: str,
        user_id: int,
        workspace_id: Optional[str],
        memory_types: Optional[List[str]],
    ) -> str:
        """Generate a cache key for the query"""
        key_parts = [
            query.lower(),
            str(user_id),
            workspace_id or "none",
            ",".join(memory_types or ["all"]),
        ]
        return "|".join(key_parts)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.retrieval_cache:
            return False
        
        timestamp = self.retrieval_cache.get(f"{cache_key}_timestamp")
        if not timestamp:
            return False
        
        age = (datetime.utcnow() - timestamp).total_seconds()
        return age < self.cache_ttl
    
    def _set_cache_timestamp(self, cache_key: str):
        """Set timestamp for cache entry"""
        self.retrieval_cache[f"{cache_key}_timestamp"] = datetime.utcnow()
    
    def clear_cache(self):
        """Clear the retrieval cache"""
        self.retrieval_cache.clear()
    
    def assemble_context(
        self,
        matches: List[MemoryMatch],
        max_context_length: int = 4000,
    ) -> str:
        """
        Assemble context from ranked matches.
        
        Args:
            matches: Ranked memory matches
            max_context_length: Maximum total context length
        
        Returns:
            Assembled context string
        """
        context_parts = []
        total_length = 0
        
        for match in matches:
            content = f"[{match.memory_type}] {match.content}"
            
            if total_length + len(content) <= max_context_length:
                context_parts.append(content)
                total_length += len(content)
            else:
                break
        
        return "\n\n".join(context_parts)
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about retrieval operations"""
        return {
            "cached_queries": len([k for k in self.retrieval_cache.keys() if not k.endswith("_timestamp")]),
            "registered_stores": list(self.memory_stores.keys()),
            "cache_ttl_seconds": self.cache_ttl,
        }
