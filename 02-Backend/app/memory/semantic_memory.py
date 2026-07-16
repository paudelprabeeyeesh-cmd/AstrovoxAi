"""
Semantic Memory - Phase 3.2 Layer 3

Stores facts that remain true over time:
- Preferred programming language
- Favorite writing style
- Timezone
- Primary spoken language
- Preferred AI model
- Common workflow preferences

Semantic memory should update only after repeated confirmation or explicit user instruction.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class FactCategory(Enum):
    """Categories of semantic facts"""
    PREFERENCE = "preference"
    PERSONAL_INFO = "personal_info"
    WORKFLOW = "workflow"
    SETTINGS = "settings"
    KNOWLEDGE = "knowledge"


class SemanticMemory:
    """
    Stores long-term facts about the user that remain true over time.
    Updates only after confirmation or explicit instruction.
    """
    
    def __init__(self):
        self.facts: Dict[str, Dict[str, Any]] = {}
        self.confirmation_counts: Dict[str, int] = {}
    
    def add_fact(
        self,
        fact_key: str,
        fact_value: Any,
        category: FactCategory,
        confidence: float = 1.0,
        requires_confirmation: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Add or update a semantic fact.
        
        Args:
            fact_key: Unique key for the fact
            fact_value: Value of the fact
            category: Category of the fact
            confidence: Confidence level (0.0 to 1.0)
            requires_confirmation: Whether fact requires confirmation
            metadata: Additional metadata
        """
        self.facts[fact_key] = {
            "value": fact_value,
            "category": category.value,
            "confidence": confidence,
            "requires_confirmation": requires_confirmation,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "confirmation_count": self.confirmation_counts.get(fact_key, 0),
        }
    
    def confirm_fact(self, fact_key: str):
        """Confirm a fact, increasing its confidence"""
        if fact_key in self.facts:
            self.confirmation_counts[fact_key] = self.confirmation_counts.get(fact_key, 0) + 1
            self.facts[fact_key]["confirmation_count"] = self.confirmation_counts[fact_key]
            self.facts[fact_key]["updated_at"] = datetime.utcnow().isoformat()
            
            # Increase confidence based on confirmations
            confirmations = self.confirmation_counts[fact_key]
            new_confidence = min(0.5 + (confirmations * 0.1), 1.0)
            self.facts[fact_key]["confidence"] = new_confidence
    
    def get_fact(self, fact_key: str) -> Optional[Any]:
        """Get a fact by key"""
        if fact_key in self.facts:
            return self.facts[fact_key]["value"]
        return None
    
    def get_fact_details(self, fact_key: str) -> Optional[Dict[str, Any]]:
        """Get full fact details"""
        return self.facts.get(fact_key)
    
    def get_facts_by_category(self, category: FactCategory) -> Dict[str, Any]:
        """Get all facts in a category"""
        result = {}
        for key, data in self.facts.items():
            if data["category"] == category.value:
                result[key] = data["value"]
        return result
    
    def update_fact(
        self,
        fact_key: str,
        new_value: Any,
        explicit: bool = False,
    ):
        """
        Update a fact.
        
        Args:
            fact_key: Fact key
            new_value: New value
            explicit: Whether this is an explicit user instruction
        """
        if fact_key not in self.facts:
            return
        
        fact = self.facts[fact_key]
        
        # Only update if explicit or requires confirmation is met
        if explicit or not fact["requires_confirmation"]:
            fact["value"] = new_value
            fact["updated_at"] = datetime.utcnow().isoformat()
        elif fact["confidence"] >= 0.8:
            # High confidence facts can be updated
            fact["value"] = new_value
            fact["updated_at"] = datetime.utcnow().isoformat()
    
    def delete_fact(self, fact_key: str):
        """Delete a fact"""
        if fact_key in self.facts:
            del self.facts[fact_key]
        if fact_key in self.confirmation_counts:
            del self.confirmation_counts[fact_key]
    
    def search_facts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search facts by content"""
        query_lower = query.lower()
        results = []
        
        for key, data in self.facts.items():
            # Search in key
            if query_lower in key.lower():
                results.append({"key": key, **data})
                continue
            
            # Search in value (if string)
            if isinstance(data["value"], str) and query_lower in data["value"].lower():
                results.append({"key": key, **data})
        
        return results[:limit]
    
    # Convenience methods for common fact types
    
    def set_preference(self, preference_key: str, value: Any):
        """Set a user preference"""
        self.add_fact(
            fact_key=f"pref_{preference_key}",
            fact_value=value,
            category=FactCategory.PREFERENCE,
            requires_confirmation=True,
        )
    
    def get_preference(self, preference_key: str) -> Optional[Any]:
        """Get a user preference"""
        return self.get_fact(f"pref_{preference_key}")
    
    def set_personal_info(self, info_key: str, value: Any):
        """Set personal information"""
        self.add_fact(
            fact_key=f"personal_{info_key}",
            fact_value=value,
            category=FactCategory.PERSONAL_INFO,
            requires_confirmation=True,
        )
    
    def get_personal_info(self, info_key: str) -> Optional[Any]:
        """Get personal information"""
        return self.get_fact(f"personal_{info_key}")
    
    def set_workflow(self, workflow_key: str, value: Any):
        """Set a workflow preference"""
        self.add_fact(
            fact_key=f"workflow_{workflow_key}",
            fact_value=value,
            category=FactCategory.WORKFLOW,
            requires_confirmation=False,
        )
    
    def get_workflow(self, workflow_key: str) -> Optional[Any]:
        """Get a workflow preference"""
        return self.get_fact(f"workflow_{workflow_key}")
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences"""
        return self.get_facts_by_category(FactCategory.PREFERENCE)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of semantic memory"""
        by_category = {}
        for data in self.facts.values():
            category = data["category"]
            if category not in by_category:
                by_category[category] = 0
            by_category[category] += 1
        
        high_confidence = sum(
            1 for data in self.facts.values()
            if data["confidence"] >= 0.8
        )
        
        return {
            "total_facts": len(self.facts),
            "by_category": by_category,
            "high_confidence_facts": high_confidence,
            "pending_confirmation": sum(
                1 for data in self.facts.values()
                if data["requires_confirmation"] and data["confidence"] < 0.8
            ),
        }
