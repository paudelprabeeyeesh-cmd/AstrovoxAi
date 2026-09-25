"""
Hybrid Retrieval - Phase 5.8

Combines multiple retrieval methods:
- Keyword matching
- Semantic similarity
- Recency
- Authority
- User relevance
- Workspace context

This gives better results for technical and factual questions.
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta


class RetrievalMethod(Enum):
    """Methods for retrieval"""
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    HYBRID_WEIGHTED = "hybrid_weighted"


class HybridRetrieval:
    """
    Combines keyword and semantic retrieval for better results.
    Dynamically chooses the best method based on query characteristics.
    """
    
    def __init__(self):
        self.retrieval_history: List[Dict[str, Any]] = []
        self.keyword_weight = 0.4
        self.semantic_weight = 0.6
    
    def retrieve(
        self,
        query: str,
        knowledge_items: List[Dict[str, Any]],
        method: RetrievalMethod = RetrievalMethod.HYBRID,
        workspace_id: Optional[str] = None,
        user_id: Optional[int] = None,
        top_k: int = 10,
        min_relevance: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge items using hybrid approach.
        
        Args:
            query: Search query
            knowledge_items: List of knowledge items to search
            method: Retrieval method to use
            workspace_id: Optional workspace filter
            user_id: Optional user filter
            top_k: Maximum number of results
            min_relevance: Minimum relevance threshold
        
        Returns:
            Ranked list of relevant items
        """
        # Filter by workspace and user
        filtered_items = self._filter_items(knowledge_items, workspace_id, user_id)
        
        # Choose method based on query characteristics
        if method == RetrievalMethod.HYBRID:
            method = self._choose_method(query)
        
        # Retrieve using chosen method
        if method == RetrievalMethod.KEYWORD:
            results = self._keyword_retrieval(query, filtered_items, top_k)
        elif method == RetrievalMethod.SEMANTIC:
            results = self._semantic_retrieval(query, filtered_items, top_k)
        elif method == RetrievalMethod.HYBRID:
            results = self._combine_retrieval(query, filtered_items, top_k)
        elif method == RetrievalMethod.HYBRID_WEIGHTED:
            results = self._weighted_retrieval(query, filtered_items, top_k)
        else:
            results = self._keyword_retrieval(query, filtered_items, top_k)
        
        # Filter by minimum relevance
        results = [r for r in results if r["relevance_score"] >= min_relevance]
        
        # Log retrieval
        self._log_retrieval(query, method, len(results))
        
        return results[:top_k]
    
    def _filter_items(
        self,
        items: List[Dict[str, Any]],
        workspace_id: Optional[str],
        user_id: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Filter items by workspace and user"""
        filtered = items
        
        if workspace_id:
            filtered = [item for item in filtered if item.get("workspace_id") == workspace_id]
        
        if user_id:
            filtered = [item for item in filtered if item.get("owner_id") == user_id]
        
        return filtered
    
    def _choose_method(self, query: str) -> RetrievalMethod:
        """Choose the best retrieval method based on query characteristics"""
        query_lower = query.lower()
        
        # Check for specific technical terms (keyword-heavy)
        technical_indicators = [
            "function", "method", "class", "variable", "parameter",
            "api", "endpoint", "url", "path", "query",
            "formula", "equation", "theorem", "definition",
        ]
        
        has_technical = any(indicator in query_lower for indicator in technical_indicators)
        
        # Check for conceptual questions (semantic-heavy)
        conceptual_indicators = [
            "explain", "describe", "what is", "how does", "why",
            "understand", "concept", "principle", "overview",
        ]
        
        has_conceptual = any(indicator in query_lower for indicator in conceptual_indicators)
        
        # Choose method
        if has_technical and not has_conceptual:
            return RetrievalMethod.KEYWORD
        elif has_conceptual and not has_technical:
            return RetrievalMethod.SEMANTIC
        else:
            return RetrievalMethod.HYBRID_WEIGHTED
    
    def _keyword_retrieval(
        self,
        query: str,
        items: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Retrieve using keyword matching"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_items = []
        
        for item in items:
            content = item.get("content", "").lower()
            title = item.get("title", "").lower()
            
            # Calculate keyword match score
            content_words = set(content.split())
            title_words = set(title.split())
            
            # Title matches are more important
            title_matches = len(query_words & title_words)
            content_matches = len(query_words & content_words)
            
            # Calculate score
            score = (title_matches * 2.0 + content_matches) / len(query_words)
            
            # Boost for exact phrase matches
            if query_lower in content:
                score += 0.5
            if query_lower in title:
                score += 1.0
            
            scored_items.append({
                **item,
                "relevance_score": min(score, 1.0),
                "retrieval_method": "keyword",
            })
        
        # Sort by score and return top_k
        scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_items[:top_k]
    
    def _semantic_retrieval(
        self,
        query: str,
        items: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Retrieve using semantic similarity"""
        # Placeholder for semantic retrieval
        # In production, this would use embeddings and vector similarity
        
        scored_items = []
        
        for item in items:
            # Simplified semantic scoring
            # In production, use actual embedding similarity
            content = item.get("content", "")
            title = item.get("title", "")
            
            # Calculate simple similarity based on word overlap
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            title_words = set(title.lower().split())
            
            overlap = len(query_words & content_words) + len(query_words & title_words)
            total_words = len(query_words) + len(content_words) + len(title_words)
            
            score = overlap / total_words if total_words > 0 else 0.0
            
            scored_items.append({
                **item,
                "relevance_score": min(score * 2, 1.0),  # Boost semantic score
                "retrieval_method": "semantic",
            })
        
        scored_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_items[:top_k]
    
    def _combine_retrieval(
        self,
        query: str,
        items: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Combine keyword and semantic retrieval"""
        keyword_results = self._keyword_retrieval(query, items, top_k * 2)
        semantic_results = self._semantic_retrieval(query, items, top_k * 2)
        
        # Combine and deduplicate
        combined = {}
        
        for item in keyword_results:
            item_id = item.get("id", str(item))
            if item_id not in combined:
                combined[item_id] = {
                    **item,
                    "keyword_score": item["relevance_score"],
                    "semantic_score": 0.0,
                }
            else:
                combined[item_id]["keyword_score"] = item["relevance_score"]
        
        for item in semantic_results:
            item_id = item.get("id", str(item))
            if item_id not in combined:
                combined[item_id] = {
                    **item,
                    "keyword_score": 0.0,
                    "semantic_score": item["relevance_score"],
                }
            else:
                combined[item_id]["semantic_score"] = item["relevance_score"]
        
        # Calculate combined score
        for item_id, item in combined.items():
            item["relevance_score"] = (
                self.keyword_weight * item["keyword_score"] +
                self.semantic_weight * item["semantic_score"]
            )
            item["retrieval_method"] = "hybrid"
        
        # Sort by combined score
        results = list(combined.values())
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return results[:top_k]
    
    def _weighted_retrieval(
        self,
        query: str,
        items: List[Dict[str, Any]],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Weighted retrieval with additional factors"""
        combined_results = self._combine_retrieval(query, items, top_k * 2)
        
        # Apply additional weights
        for item in combined_results:
            base_score = item["relevance_score"]
            
            # Recency boost
            upload_date = item.get("upload_date", "")
            if upload_date:
                try:
                    date = datetime.fromisoformat(upload_date)
                    days_old = (datetime.utcnow() - date).days
                    recency_boost = max(0, 1 - days_old / 365)  # Decay over a year
                    base_score *= (1 + recency_boost * 0.2)
                except:
                    pass
            
            # Importance boost
            importance = item.get("importance_score", 0.5)
            base_score *= (1 + importance * 0.3)
            
            # Authority boost (based on source quality)
            source_quality = item.get("source_quality", 0.5)
            base_score *= (1 + source_quality * 0.2)
            
            # User relevance boost
            if item.get("owner_id") == item.get("current_user_id"):
                base_score *= 1.2
            
            item["relevance_score"] = min(base_score, 1.0)
            item["retrieval_method"] = "hybrid_weighted"
        
        # Sort and return
        combined_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return combined_results[:top_k]
    
    def _log_retrieval(
        self,
        query: str,
        method: RetrievalMethod,
        result_count: int,
    ):
        """Log retrieval for analysis"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query[:100],  # Truncate for logging
            "method": method.value,
            "result_count": result_count,
        }
        self.retrieval_history.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.retrieval_history) > 1000:
            self.retrieval_history = self.retrieval_history[-1000:]
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        if not self.retrieval_history:
            return {"total_retrievals": 0}
        
        method_counts = {}
        for entry in self.retrieval_history:
            method = entry["method"]
            method_counts[method] = method_counts.get(method, 0) + 1
        
        avg_results = sum(entry["result_count"] for entry in self.retrieval_history) / len(self.retrieval_history)
        
        return {
            "total_retrievals": len(self.retrieval_history),
            "by_method": method_counts,
            "average_results": avg_results,
            "keyword_weight": self.keyword_weight,
            "semantic_weight": self.semantic_weight,
        }
    
    def adjust_weights(self, keyword_weight: float, semantic_weight: float):
        """Adjust the weights for hybrid retrieval"""
        total = keyword_weight + semantic_weight
        if total > 0:
            self.keyword_weight = keyword_weight / total
            self.semantic_weight = semantic_weight / total
    
    def get_retrieval_explanation(
        self,
        item: Dict[str, Any],
        query: str,
    ) -> str:
        """Generate explanation for why an item was retrieved"""
        method = item.get("retrieval_method", "unknown")
        score = item.get("relevance_score", 0.0)
        
        explanation_parts = [
            f"Retrieved using {method} method",
            f"Relevance score: {score:.2f}",
        ]
        
        if method == "keyword":
            explanation_parts.append("Matched based on keyword similarity")
        elif method == "semantic":
            explanation_parts.append("Matched based on semantic similarity")
        elif "hybrid" in method:
            keyword_score = item.get("keyword_score", 0.0)
            semantic_score = item.get("semantic_score", 0.0)
            explanation_parts.append(f"Keyword score: {keyword_score:.2f}, Semantic score: {semantic_score:.2f}")
        
        return ". ".join(explanation_parts)
