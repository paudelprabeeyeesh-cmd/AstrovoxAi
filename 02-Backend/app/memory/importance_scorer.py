"""
Memory Importance Scoring - Phase 3.3

Assigns importance scores based on:
- User explicitly requests it
- Frequency of repetition
- Long-term usefulness
- Emotional significance (where appropriate)
- Project relevance
- Administrative importance
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class ImportanceLevel(Enum):
    """Importance levels"""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    MINIMAL = 0.2


class ImportanceScorer:
    """
    Scores memory items based on various factors to determine
    what should be stored long-term vs. discarded.
    """
    
    def __init__(self):
        self.access_patterns: Dict[str, List[datetime]] = {}
        self.repetition_counts: Dict[str, int] = {}
    
    def score_memory(
        self,
        content: str,
        memory_type: str,
        user_explicit: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate importance score for a memory item.
        
        Args:
            content: Memory content
            memory_type: Type of memory (semantic, episodic, etc.)
            user_explicit: Whether user explicitly requested storage
            context: Additional context
        
        Returns:
            Importance score (0.0 to 1.0)
        """
        score = 0.0
        context = context or {}
        
        # Factor 1: User explicit request (highest weight)
        if user_explicit:
            score += 0.4
        
        # Factor 2: Repetition frequency
        repetition_score = self._get_repetition_score(content)
        score += repetition_score * 0.3
        
        # Factor 3: Long-term usefulness
        usefulness_score = self._assess_usefulness(content, memory_type)
        score += usefulness_score * 0.2
        
        # Factor 4: Project relevance
        if context.get("project_relevance"):
            score += 0.1
        
        # Factor 5: Administrative importance
        if context.get("administrative"):
            score += 0.1
        
        # Factor 6: Content characteristics
        content_score = self._analyze_content_characteristics(content)
        score += content_score * 0.1
        
        # Clamp to 0-1 range
        return min(max(score, 0.0), 1.0)
    
    def _get_repetition_score(self, content: str) -> float:
        """Calculate score based on repetition frequency"""
        content_hash = self._hash_content(content)
        count = self.repetition_counts.get(content_hash, 0)
        
        # More repetitions = higher score, with diminishing returns
        if count == 0:
            return 0.0
        elif count == 1:
            return 0.3
        elif count == 2:
            return 0.6
        elif count <= 5:
            return 0.8
        else:
            return 1.0
    
    def _assess_usefulness(self, content: str, memory_type: str) -> float:
        """Assess long-term usefulness of content"""
        content_lower = content.lower()
        
        # Semantic facts are generally useful
        if memory_type == "semantic":
            # Check for preference-like content
            preference_keywords = ["prefer", "like", "favorite", "usually", "always"]
            if any(keyword in content_lower for keyword in preference_keywords):
                return 0.9
            
            # Check for factual information
            fact_keywords = ["is", "are", "was", "were", "have", "has"]
            if any(keyword in content_lower for keyword in fact_keywords):
                return 0.7
        
        # Episodic events are useful if significant
        elif memory_type == "episodic":
            milestone_keywords = ["completed", "finished", "achieved", "milestone", "launched"]
            if any(keyword in content_lower for keyword in milestone_keywords):
                return 0.9
        
        # Procedural memory is always useful
        elif memory_type == "procedural":
            return 0.8
        
        # Default moderate usefulness
        return 0.5
    
    def _analyze_content_characteristics(self, content: str) -> float:
        """Analyze content for importance indicators"""
        content_lower = content.lower()
        
        # High importance indicators
        high_importance = [
            "important", "critical", "essential", "must", "required",
            "remember", "don't forget", "key", "main",
        ]
        
        # Low importance indicators
        low_importance = [
            "just", "only", "maybe", "perhaps", "might", "could be",
            "temporary", "for now", "currently",
        ]
        
        high_count = sum(1 for keyword in high_importance if keyword in content_lower)
        low_count = sum(1 for keyword in low_importance if keyword in content_lower)
        
        score = 0.5 + (high_count * 0.2) - (low_count * 0.3)
        return min(max(score, 0.0), 1.0)
    
    def _hash_content(self, content: str) -> str:
        """Create a simple hash of content for tracking repetitions"""
        # Simple hash for demonstration
        return str(hash(content.lower().strip()))
    
    def record_access(self, memory_id: str):
        """Record access to a memory item"""
        if memory_id not in self.access_patterns:
            self.access_patterns[memory_id] = []
        self.access_patterns[memory_id].append(datetime.utcnow())
        
        # Keep only last 100 accesses
        if len(self.access_patterns[memory_id]) > 100:
            self.access_patterns[memory_id] = self.access_patterns[memory_id][-100:]
    
    def record_repetition(self, content: str):
        """Record a repetition of content"""
        content_hash = self._hash_content(content)
        self.repetition_counts[content_hash] = self.repetition_counts.get(content_hash, 0) + 1
    
    def get_access_frequency(self, memory_id: str, days: int = 30) -> float:
        """
        Calculate access frequency for a memory item.
        
        Args:
            memory_id: Memory ID
            days: Number of days to look back
        
        Returns:
            Accesses per day
        """
        if memory_id not in self.access_patterns:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_accesses = [
            access for access in self.access_patterns[memory_id]
            if access >= cutoff
        ]
        
        return len(recent_accesses) / days
    
    def should_retain(
        self,
        score: float,
        memory_type: str,
        age_days: int = 0,
    ) -> bool:
        """
        Determine if a memory should be retained based on score and age.
        
        Args:
            score: Importance score
            memory_type: Type of memory
            age_days: Age of memory in days
        
        Returns:
            Whether to retain the memory
        """
        # Critical and high importance always retained
        if score >= 0.8:
            return True
        
        # Medium importance retained for 90 days
        if score >= 0.6 and age_days < 90:
            return True
        
        # Low importance retained for 30 days
        if score >= 0.4 and age_days < 30:
            return True
        
        # Minimal importance retained for 7 days
        if score >= 0.2 and age_days < 7:
            return True
        
        # Context memory is always short-term
        if memory_type == "context":
            return age_days < 1
        
        return False
    
    def get_importance_level(self, score: float) -> ImportanceLevel:
        """Convert score to importance level"""
        if score >= 1.0:
            return ImportanceLevel.CRITICAL
        elif score >= 0.8:
            return ImportanceLevel.HIGH
        elif score >= 0.6:
            return ImportanceLevel.MEDIUM
        elif score >= 0.4:
            return ImportanceLevel.LOW
        else:
            return ImportanceLevel.MINIMAL
    
    def decay_score(
        self,
        original_score: float,
        age_days: int,
        memory_type: str,
    ) -> float:
        """
        Apply time-based decay to importance score.
        
        Args:
            original_score: Original importance score
            age_days: Age in days
            memory_type: Type of memory
        
        Returns:
            Decayed score
        """
        # Different decay rates for different memory types
        decay_rates = {
            "context": 0.9,  # Fast decay
            "conversation": 0.95,
            "semantic": 0.99,  # Slow decay
            "episodic": 0.98,
            "procedural": 0.995,  # Very slow decay
            "workspace": 0.97,
        }
        
        decay_rate = decay_rates.get(memory_type, 0.97)
        
        # Apply exponential decay
        decayed_score = original_score * (decay_rate ** age_days)
        
        return decayed_score
    
    def get_storage_recommendation(
        self,
        content: str,
        memory_type: str,
        current_score: float,
        age_days: int = 0,
    ) -> Dict[str, Any]:
        """
        Get storage recommendation for a memory item.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            current_score: Current importance score
            age_days: Age in days
        
        Returns:
            Storage recommendation
        """
        # Apply decay
        decayed_score = self.decay_score(current_score, age_days, memory_type)
        
        # Check if should retain
        should_retain = self.should_retain(decayed_score, memory_type, age_days)
        
        # Get importance level
        level = self.get_importance_level(decayed_score)
        
        # Determine action
        if not should_retain:
            action = "delete"
        elif decayed_score < current_score * 0.5:
            action = "archive"
        else:
            action = "retain"
        
        return {
            "original_score": current_score,
            "decayed_score": decayed_score,
            "importance_level": level.value,
            "should_retain": should_retain,
            "recommended_action": action,
            "reason": self._get_recommendation_reason(action, level, age_days),
        }
    
    def _get_recommendation_reason(
        self,
        action: str,
        level: ImportanceLevel,
        age_days: int,
    ) -> str:
        """Get explanation for recommendation"""
        if action == "delete":
            return f"Score has decayed to {level.value} level after {age_days} days"
        elif action == "archive":
            return f"Score has significantly decayed, archiving recommended"
        else:
            return f"Memory remains at {level.value} importance level"
