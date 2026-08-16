"""
Enhanced Vector Search Layer - Phase 5.7

Advanced vector search features:
- Semantic similarity search
- Hybrid search
- Metadata filters
- Source ranking
- Re-ranking by relevance

Vector search should be combined with keyword search, not used alone.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np


class SearchMethod(Enum):
    """Methods for vector search"""
    PURE_SEMANTIC = "pure_semantic"
    HYBRID = "hybrid"
    RERANKED = "reranked"
    FILTERED = "filtered"


class EnhancedVectorSearch:
    """
    Enhanced vector search with advanced features.
    Supports semantic similarity, hybrid search, metadata filtering, and re-ranking.
    """
    
    def __init__(self, embedding_dimension: int = 1536):
        self.embedding_dimension = embedding_dimension
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.search_history: List[Dict[str, Any]] = []
    
    def add_embedding(
        self,
        embedding_id: str,
        embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add an embedding with metadata"""
        if embedding.shape[0] != self.embedding_dimension:
            raise ValueError(f"Embedding dimension mismatch. Expected {self.embedding_dimension}, got {embedding.shape[0]}")
        
        self.embeddings[embedding_id] = embedding
        self.metadata[embedding_id] = {
            "embedding_id": embedding_id,
            "added_at": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }
    
    def semantic_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        min_similarity: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Pure semantic similarity search.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of (embedding_id, similarity_score) tuples
        """
        if query_embedding.shape[0] != self.embedding_dimension:
            raise ValueError(f"Query embedding dimension mismatch")
        
        similarities = []
        
        for embedding_id, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            if similarity >= min_similarity:
                similarities.append((embedding_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def hybrid_search(
        self,
        query_embedding: np.ndarray,
        query_keywords: List[str],
        top_k: int = 10,
        semantic_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ) -> List[Tuple[str, float]]:
        """
        Hybrid search combining semantic and keyword matching.
        
        Args:
            query_embedding: Query embedding vector
            query_keywords: Keywords for matching
            top_k: Number of results
            semantic_weight: Weight for semantic similarity
            keyword_weight: Weight for keyword matching
        
        Returns:
            List of (embedding_id, combined_score) tuples
        """
        # Get semantic scores
        semantic_results = self.semantic_search(query_embedding, top_k * 2, min_similarity=0.0)
        semantic_scores = {embedding_id: score for embedding_id, score in semantic_results}
        
        # Get keyword scores
        keyword_scores = self._keyword_search(query_keywords)
        
        # Combine scores
        combined_scores = {}
        
        # Process semantic results
        for embedding_id, semantic_score in semantic_scores.items():
            keyword_score = keyword_scores.get(embedding_id, 0.0)
            combined_score = (
                semantic_weight * semantic_score +
                keyword_weight * keyword_score
            )
            combined_scores[embedding_id] = combined_score
        
        # Add keyword-only results
        for embedding_id, keyword_score in keyword_scores.items():
            if embedding_id not in combined_scores:
                combined_scores[embedding_id] = keyword_weight * keyword_score
        
        # Sort by combined score
        results = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def filtered_search(
        self,
        query_embedding: np.ndarray,
        filters: Dict[str, Any],
        top_k: int = 10,
        min_similarity: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Semantic search with metadata filtering.
        
        Args:
            query_embedding: Query embedding vector
            filters: Metadata filters (e.g., {"category": "medical", "language": "en"})
            top_k: Number of results
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of (embedding_id, similarity_score) tuples
        """
        # Filter embeddings by metadata
        filtered_ids = self._filter_by_metadata(filters)
        
        if not filtered_ids:
            return []
        
        # Search only filtered embeddings
        similarities = []
        
        for embedding_id in filtered_ids:
            if embedding_id not in self.embeddings:
                continue
            
            embedding = self.embeddings[embedding_id]
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            if similarity >= min_similarity:
                similarities.append((embedding_id, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def reranked_search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        rerank_factors: Optional[Dict[str, float]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Semantic search with re-ranking based on additional factors.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results
            rerank_factors: Factors for re-ranking (e.g., {"recency": 0.2, "importance": 0.3})
        
        Returns:
            List of (embedding_id, reranked_score) tuples
        """
        rerank_factors = rerank_factors or {
            "recency": 0.1,
            "importance": 0.2,
            "source_quality": 0.1,
        }
        
        # Get initial semantic results
        initial_results = self.semantic_search(query_embedding, top_k * 2, min_similarity=0.0)
        
        # Re-rank based on factors
        reranked_results = []
        
        for embedding_id, semantic_score in initial_results:
            metadata = self.metadata.get(embedding_id, {})
            
            # Apply re-ranking factors
            reranked_score = semantic_score
            
            # Recency boost
            if "recency" in rerank_factors and rerank_factors["recency"] > 0:
                recency_boost = self._calculate_recency_boost(metadata)
                reranked_score *= (1 + recency_boost * rerank_factors["recency"])
            
            # Importance boost
            if "importance" in rerank_factors and rerank_factors["importance"] > 0:
                importance = metadata.get("importance_score", 0.5)
                reranked_score *= (1 + importance * rerank_factors["importance"])
            
            # Source quality boost
            if "source_quality" in rerank_factors and rerank_factors["source_quality"] > 0:
                source_quality = metadata.get("source_quality", 0.5)
                reranked_score *= (1 + source_quality * rerank_factors["source_quality"])
            
            reranked_results.append((embedding_id, min(reranked_score, 1.0)))
        
        # Sort by reranked score
        reranked_results.sort(key=lambda x: x[1], reverse=True)
        
        return reranked_results[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _keyword_search(self, keywords: List[str]) -> Dict[str, float]:
        """Search by keywords in metadata"""
        keyword_scores = {}
        
        for embedding_id, metadata in self.metadata.items():
            score = 0.0
            
            # Search in content
            content = metadata.get("content", "").lower()
            for keyword in keywords:
                if keyword.lower() in content:
                    score += 1.0
            
            # Search in title
            title = metadata.get("title", "").lower()
            for keyword in keywords:
                if keyword.lower() in title:
                    score += 2.0  # Title matches are more important
            
            # Normalize score
            if score > 0:
                keyword_scores[embedding_id] = min(score / (len(keywords) * 3), 1.0)
        
        return keyword_scores
    
    def _filter_by_metadata(self, filters: Dict[str, Any]) -> List[str]:
        """Filter embedding IDs by metadata criteria"""
        filtered_ids = []
        
        for embedding_id, metadata in self.metadata.items():
            match = True
            
            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    match = False
                    break
            
            if match:
                filtered_ids.append(embedding_id)
        
        return filtered_ids
    
    def _calculate_recency_boost(self, metadata: Dict[str, Any]) -> float:
        """Calculate recency boost based on added_at timestamp"""
        added_at = metadata.get("added_at", "")
        
        if not added_at:
            return 0.0
        
        try:
            from datetime import datetime
            date = datetime.fromisoformat(added_at)
            days_old = (datetime.utcnow() - date).days
            
            # Decay over 90 days
            boost = max(0, 1 - days_old / 90)
            return boost
        
        except:
            return 0.0
    
    def source_ranking(
        self,
        query_embedding: np.ndarray,
        source_priorities: Dict[str, float],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Semantic search with source-based ranking.
        
        Args:
            query_embedding: Query embedding vector
            source_priorities: Priority scores for sources (e.g., {"textbook": 1.5, "web": 1.0})
            top_k: Number of results
        
        Returns:
            List of (embedding_id, ranked_score) tuples
        """
        # Get initial semantic results
        initial_results = self.semantic_search(query_embedding, top_k * 2, min_similarity=0.0)
        
        # Apply source priorities
        ranked_results = []
        
        for embedding_id, semantic_score in initial_results:
            metadata = self.metadata.get(embedding_id, {})
            source_type = metadata.get("source_type", "unknown")
            
            # Get source priority
            priority = source_priorities.get(source_type, 1.0)
            
            # Apply priority
            ranked_score = semantic_score * priority
            
            ranked_results.append((embedding_id, min(ranked_score, 1.0)))
        
        # Sort by ranked score
        ranked_results.sort(key=lambda x: x[1], reverse=True)
        
        return ranked_results[:top_k]
    
    def advanced_search(
        self,
        query_embedding: np.ndarray,
        query_keywords: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        source_priorities: Optional[Dict[str, float]] = None,
        rerank_factors: Optional[Dict[str, float]] = None,
        method: SearchMethod = SearchMethod.HYBRID,
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Advanced search combining all features.
        
        Args:
            query_embedding: Query embedding vector
            query_keywords: Optional keywords for hybrid search
            filters: Optional metadata filters
            source_priorities: Optional source priorities
            rerank_factors: Optional re-ranking factors
            method: Search method to use
            top_k: Number of results
        
        Returns:
            List of (embedding_id, score) tuples
        """
        # Apply filters if provided
        if filters:
            results = self.filtered_search(query_embedding, filters, top_k * 2, min_similarity=0.0)
        else:
            results = self.semantic_search(query_embedding, top_k * 2, min_similarity=0.0)
        
        # Convert to dict for further processing
        result_scores = {embedding_id: score for embedding_id, score in results}
        
        # Apply hybrid search if keywords provided
        if query_keywords and method in [SearchMethod.HYBRID, SearchMethod.RERANKED]:
            keyword_scores = self._keyword_search(query_keywords)
            
            for embedding_id, keyword_score in keyword_scores.items():
                if embedding_id in result_scores:
                    result_scores[embedding_id] = (
                        0.6 * result_scores[embedding_id] +
                        0.4 * keyword_score
                    )
                else:
                    result_scores[embedding_id] = 0.4 * keyword_score
        
        # Apply source priorities if provided
        if source_priorities:
            for embedding_id in list(result_scores.keys()):
                metadata = self.metadata.get(embedding_id, {})
                source_type = metadata.get("source_type", "unknown")
                priority = source_priorities.get(source_type, 1.0)
                result_scores[embedding_id] *= priority
        
        # Apply re-ranking if requested
        if rerank_factors and method == SearchMethod.RERANKED:
            for embedding_id in list(result_scores.keys()):
                metadata = self.metadata.get(embedding_id, {})
                
                # Recency
                if "recency" in rerank_factors:
                    recency_boost = self._calculate_recency_boost(metadata)
                    result_scores[embedding_id] *= (1 + recency_boost * rerank_factors["recency"])
                
                # Importance
                if "importance" in rerank_factors:
                    importance = metadata.get("importance_score", 0.5)
                    result_scores[embedding_id] *= (1 + importance * rerank_factors["importance"])
        
        # Sort and return
        sorted_results = sorted(result_scores.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_results[:top_k]
    
    def get_embedding(self, embedding_id: str) -> Optional[np.ndarray]:
        """Get an embedding by ID"""
        return self.embeddings.get(embedding_id)
    
    def get_metadata(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata by embedding ID"""
        return self.metadata.get(embedding_id)
    
    def delete_embedding(self, embedding_id: str):
        """Delete an embedding"""
        if embedding_id in self.embeddings:
            del self.embeddings[embedding_id]
        if embedding_id in self.metadata:
            del self.metadata[embedding_id]
    
    def update_metadata(self, embedding_id: str, metadata: Dict[str, Any]):
        """Update metadata for an embedding"""
        if embedding_id in self.metadata:
            self.metadata[embedding_id].update(metadata)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get search statistics"""
        return {
            "total_embeddings": len(self.embeddings),
            "embedding_dimension": self.embedding_dimension,
            "by_source_type": self._count_by_source_type(),
            "by_category": self._count_by_category(),
            "search_count": len(self.search_history),
        }
    
    def _count_by_source_type(self) -> Dict[str, int]:
        """Counts embeddings by source type"""
        counts = {}
        for metadata in self.metadata.values():
            source_type = metadata.get("source_type", "unknown")
            counts[source_type] = counts.get(source_type, 0) + 1
        return counts
    
    def _count_by_category(self) -> Dict[str, int]:
        """Count embeddings by category"""
        counts = {}
        for metadata in self.metadata.values():
            category = metadata.get("category", "unknown")
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    def batch_add_embeddings(
        self,
        embeddings: Dict[str, np.ndarray],
        metadata_list: Dict[str, Dict[str, Any]],
    ):
        """Add multiple embeddings at once"""
        for embedding_id, embedding in embeddings.items():
            metadata = metadata_list.get(embedding_id, {})
            self.add_embedding(embedding_id, embedding, metadata)
    
    def clear_all(self):
        """Clear all embeddings and metadata"""
        self.embeddings.clear()
        self.metadata.clear()
