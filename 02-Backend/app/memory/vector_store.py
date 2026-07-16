"""
Vector Database Integration - Phase 3.10

Stores embeddings separately from relational data using pgvector.
Metadata includes:
- Memory ID
- Category
- Timestamp
- Workspace
- Tags
- Importance score
- Embedding vector
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import numpy as np


class VectorStore:
    """
    Vector database for semantic search and similarity matching.
    Stores embeddings for efficient retrieval of similar memories.
    """
    
    def __init__(self):
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.embedding_dimension = 1536  # OpenAI embedding dimension
    
    def add_embedding(
        self,
        memory_id: str,
        embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add an embedding to the vector store.
        
        Args:
            memory_id: Unique memory identifier
            embedding: Embedding vector
            metadata: Additional metadata
        """
        if embedding.shape[0] != self.embedding_dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.embedding_dimension}, got {embedding.shape[0]}")
        
        self.embeddings[memory_id] = embedding
        self.metadata[memory_id] = {
            "memory_id": memory_id,
            "added_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }
    
    def get_embedding(self, memory_id: str) -> Optional[np.ndarray]:
        """Get an embedding by memory ID"""
        return self.embeddings.get(memory_id)
    
    def get_metadata(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a memory"""
        return self.metadata.get(memory_id)
    
    def similarity_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        memory_type: Optional[str] = None,
        workspace_id: Optional[str] = None,
        min_similarity: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Find similar memories using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            memory_type: Optional memory type filter
            workspace_id: Optional workspace filter
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of (memory_id, similarity_score) tuples
        """
        if query_embedding.shape[0] != self.embedding_dimension:
            raise ValueError(f"Query embedding dimension mismatch")
        
        similarities = []
        
        for memory_id, embedding in self.embeddings.items():
            # Apply filters
            if memory_type and self.metadata[memory_id].get("memory_type") != memory_type:
                continue
            if workspace_id and self.metadata[memory_id].get("workspace_id") != workspace_id:
                continue
            
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            if similarity >= min_similarity:
                similarities.append((memory_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def delete_embedding(self, memory_id: str):
        """Delete an embedding from the store"""
        if memory_id in self.embeddings:
            del self.embeddings[memory_id]
        if memory_id in self.metadata:
            del self.metadata[memory_id]
    
    def update_metadata(self, memory_id: str, metadata: Dict[str, Any]):
        """Update metadata for a memory"""
        if memory_id in self.metadata:
            self.metadata[memory_id].update(metadata)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        return {
            "total_embeddings": len(self.embeddings),
            "embedding_dimension": self.embedding_dimension,
            "by_memory_type": self._count_by_memory_type(),
            "by_workspace": self._count_by_workspace(),
        }
    
    def _count_by_memory_type(self) -> Dict[str, int]:
        """Count embeddings by memory type"""
        counts = {}
        for metadata in self.metadata.values():
            memory_type = metadata.get("memory_type", "unknown")
            counts[memory_type] = counts.get(memory_type, 0) + 1
        return counts
    
    def _count_by_workspace(self) -> Dict[str, int]:
        """Count embeddings by workspace"""
        counts = {}
        for metadata in self.metadata.values():
            workspace_id = metadata.get("workspace_id", "none")
            counts[workspace_id] = counts.get(workspace_id, 0) + 1
        return counts
    
    def batch_add_embeddings(
        self,
        embeddings: Dict[str, np.ndarray],
        metadata_list: Dict[str, Dict[str, Any]],
    ):
        """Add multiple embeddings at once"""
        for memory_id, embedding in embeddings.items():
            metadata = metadata_list.get(memory_id, {})
            self.add_embedding(memory_id, embedding, metadata)
    
    def clear_all(self):
        """Clear all embeddings and metadata"""
        self.embeddings.clear()
        self.metadata.clear()
    
    def export_embeddings(self, memory_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Export embeddings for backup or transfer.
        
        Args:
            memory_ids: Optional list of specific memory IDs to export
        
        Returns:
            Dictionary with embeddings and metadata
        """
        ids_to_export = memory_ids or list(self.embeddings.keys())
        
        return {
            "embeddings": {
                memory_id: self.embeddings[memory_id].tolist()
                for memory_id in ids_to_export
                if memory_id in self.embeddings
            },
            "metadata": {
                memory_id: self.metadata[memory_id]
                for memory_id in ids_to_export
                if memory_id in self.metadata
            },
            "exported_at": datetime.utcnow().isoformat(),
            "count": len(ids_to_export),
        }
    
    def import_embeddings(self, data: Dict[str, Any]):
        """
        Import embeddings from exported data.
        
        Args:
            data: Dictionary with embeddings and metadata
        """
        embeddings_data = data.get("embeddings", {})
        metadata_data = data.get("metadata", {})
        
        for memory_id, embedding_list in embeddings_data.items():
            embedding = np.array(embedding_list)
            metadata = metadata_data.get(memory_id, {})
            self.add_embedding(memory_id, embedding, metadata)
