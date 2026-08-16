"""
Domain Knowledge Packs - Phase 5.11

To make Astrovox stronger in specific fields, create knowledge packs.

Education Pack:
- textbooks
- formulas
- solved examples
- exam prep material
- question banks

Medical Pack:
- anatomy
- physiology
- terminology
- safe medical references
- clinical education sources

Programming Pack:
- API docs
- language references
- frameworks
- GitHub codebases
- best practices

Trading Pack:
- market structure
- chart patterns
- risk management
- macroeconomics
- strategy notes

Each pack can have custom retrieval logic and answer templates.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class KnowledgePackType(Enum):
    """Types of knowledge packs"""
    EDUCATION = "education"
    MEDICAL = "medical"
    PROGRAMMING = "programming"
    TRADING = "trading"
    BUSINESS = "business"
    RESEARCH = "research"
    GENERAL = "general"


class KnowledgePack:
    """
    A curated collection of knowledge for a specific domain.
    Provides specialized retrieval logic and answer templates.
    """
    
    def __init__(
        self,
        pack_id: str,
        pack_type: KnowledgePackType,
        name: str,
        description: str,
        knowledge_items: List[Dict[str, Any]],
        retrieval_strategy: str = "semantic",
        answer_template: Optional[str] = None,
    ):
        self.pack_id = pack_id
        self.pack_type = pack_type
        self.name = name
        self.description = description
        self.knowledge_items = knowledge_items
        self.retrieval_strategy = retrieval_strategy
        self.answer_template = answer_template
        self.created_at = datetime.utcnow().isoformat()
        self.last_updated = datetime.utcnow().isoformat()
    
    def add_knowledge_item(self, item: Dict[str, Any]):
        """Add a knowledge item to the pack"""
        self.knowledge_items.append(item)
        self.last_updated = datetime.utcnow().isoformat()
    
    def remove_knowledge_item(self, item_id: str):
        """Remove a knowledge item from the pack"""
        self.knowledge_items = [
            item for item in self.knowledge_items
            if item.get("id") != item_id
        ]
        self.last_updated = datetime.utcnow().isoformat()
    
    def get_knowledge_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific knowledge item"""
        for item in self.knowledge_items:
            if item.get("id") == item_id:
                return item
        return None
    
    def search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search within the knowledge pack"""
        query_lower = query.lower()
        results = []
        
        for item in self.knowledge_items:
            content = item.get("content", "").lower()
            title = item.get("title", "").lower()
            
            if query_lower in content or query_lower in title:
                results.append(item)
        
        return results[:limit]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pack statistics"""
        by_type = {}
        for item in self.knowledge_items:
            item_type = item.get("type", "unknown")
            by_type[item_type] = by_type.get(item_type, 0) + 1
        
        return {
            "pack_id": self.pack_id,
            "total_items": len(self.knowledge_items),
            "by_type": by_type,
            "retrieval_strategy": self.retrieval_strategy,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }


class KnowledgePackManager:
    """
    Manages domain-specific knowledge packs.
    Provides pre-configured packs for common domains.
    """
    
    def __init__(self):
        self.packs: Dict[str, KnowledgePack] = {}
        self.next_pack_id = 1
        
        # Initialize default packs
        self._initialize_default_packs()
    
    def _initialize_default_packs(self):
        """Initialize default knowledge packs"""
        
        # Education Pack
        education_items = [
            {
                "id": "edu_1",
                "type": "formula",
                "title": "Quadratic Formula",
                "content": "x = (-b ± √(b² - 4ac)) / 2a",
                "category": "mathematics",
            },
            {
                "id": "edu_2",
                "type": "concept",
                "title": "Newton's Laws of Motion",
                "content": "1. Law of Inertia: An object at rest stays at rest, and an object in motion stays in motion unless acted upon by an external force. 2. Law of Acceleration: F = ma. 3. Law of Action-Reaction: For every action, there is an equal and opposite reaction.",
                "category": "physics",
            },
        ]
        
        self.create_pack(
            pack_type=KnowledgePackType.EDUCATION,
            name="Education Pack",
            description="Curated educational content including formulas, concepts, and examples",
            knowledge_items=education_items,
            retrieval_strategy="semantic",
        )
        
        # Medical Pack
        medical_items = [
            {
                "id": "med_1",
                "type": "anatomy",
                "title": "Heart Structure",
                "content": "The heart has four chambers: right atrium, right ventricle, left atrium, and left ventricle. It pumps blood through the circulatory system.",
                "category": "anatomy",
            },
            {
                "id": "med_2",
                "type": "physiology",
                "title": "Blood Pressure Ranges",
                "content": "Normal blood pressure: 120/80 mmHg. Hypertension: 140/90 mmHg or higher. Hypotension: 90/60 mmHg or lower.",
                "category": "physiology",
            },
        ]
        
        self.create_pack(
            pack_type=KnowledgePackType.MEDICAL,
            name="Medical Pack",
            description="Medical knowledge including anatomy, physiology, and terminology",
            knowledge_items=medical_items,
            retrieval_strategy="semantic",
            answer_template="Based on medical knowledge: {answer} ⚠️ For educational purposes only. Consult healthcare professionals for medical advice.",
        )
        
        # Programming Pack
        programming_items = [
            {
                "id": "prog_1",
                "type": "pattern",
                "title": "MVC Pattern",
                "content": "Model-View-Controller: A software architectural pattern that separates an application into three main logical components: the Model, the View, and the Controller.",
                "category": "architecture",
            },
            {
                "id": "prog_2",
                "type": "best_practice",
                "title": "DRY Principle",
                "content": "Don't Repeat Yourself: Every piece of knowledge must have a single, unambiguous, authoritative representation within a system.",
                "category": "best_practices",
            },
        ]
        
        self.create_pack(
            pack_type=KnowledgePackType.PROGRAMMING,
            name="Programming Pack",
            description="Programming knowledge including patterns, best practices, and frameworks",
            knowledge_items=programming_items,
            retrieval_strategy="keyword",
            answer_template="According to programming best practices: {answer}",
        )
        
        # Trading Pack
        trading_items = [
            {
                "id": "trade_1",
                "type": "concept",
                "title": "Support and Resistance",
                "content": "Support: Price level where buying interest is strong enough to prevent further decline. Resistance: Price level where selling pressure is strong enough to prevent further advance.",
                "category": "technical_analysis",
            },
            {
                "id": "trade_2",
                "type": "risk_management",
                "title": "Position Sizing",
                "content": "Position sizing determines how much to invest in a trade based on risk tolerance and account size. Common methods include fixed dollar amount, percentage of account, and volatility-based sizing.",
                "category": "risk_management",
            },
        ]
        
        self.create_pack(
            pack_type=KnowledgePackType.TRADING,
            name="Trading Pack",
            description="Trading knowledge including technical analysis, risk management, and market concepts",
            knowledge_items=trading_items,
            retrieval_strategy="semantic",
            answer_template="Based on trading knowledge: {answer} ⚠️ Not financial advice. Trading involves risk.",
        )
    
    def create_pack(
        self,
        pack_type: KnowledgePackType,
        name: str,
        description: str,
        knowledge_items: List[Dict[str, Any]],
        retrieval_strategy: str = "semantic",
        answer_template: Optional[str] = None,
    ) -> KnowledgePack:
        """
        Create a new knowledge pack.
        
        Args:
            pack_type: Type of knowledge pack
            name: Name of the pack
            description: Description of the pack
            knowledge_items: Initial knowledge items
            retrieval_strategy: Strategy for retrieving from this pack
            answer_template: Template for formatting answers from this pack
        
        Returns:
            Created knowledge pack
        """
        pack_id = f"pack_{self.next_pack_id}"
        self.next_pack_id += 1
        
        pack = KnowledgePack(
            pack_id=pack_id,
            pack_type=pack_type,
            name=name,
            description=description,
            knowledge_items=knowledge_items,
            retrieval_strategy=retrieval_strategy,
            answer_template=answer_template,
        )
        
        self.packs[pack_id] = pack
        return pack
    
    def get_pack(self, pack_id: str) -> Optional[KnowledgePack]:
        """Get a knowledge pack by ID"""
        return self.packs.get(pack_id)
    
    def get_packs_by_type(self, pack_type: KnowledgePackType) -> List[KnowledgePack]:
        """Get all packs of a specific type"""
        return [
            pack for pack in self.packs.values()
            if pack.pack_type == pack_type
        ]
    
    def get_all_packs(self) -> List[KnowledgePack]:
        """Get all knowledge packs"""
        return list(self.packs.values())
    
    def delete_pack(self, pack_id: str) -> bool:
        """Delete a knowledge pack"""
        if pack_id in self.packs:
            del self.packs[pack_id]
            return True
        return False
    
    def search_all_packs(
        self,
        query: str,
        pack_types: Optional[List[KnowledgePackType]] = None,
        limit_per_pack: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across all knowledge packs.
        
        Args:
            query: Search query
            pack_types: Optional filter by pack types
            limit_per_pack: Maximum results per pack
        
        Returns:
            Dictionary mapping pack IDs to results
        """
        results = {}
        
        packs_to_search = self.packs.values()
        if pack_types:
            packs_to_search = [p for p in packs_to_search if p.pack_type in pack_types]
        
        for pack in packs_to_search:
            pack_results = pack.search_knowledge(query, limit_per_pack)
            if pack_results:
                results[pack.pack_id] = pack_results
        
        return results
    
    def get_relevant_pack(
        self,
        query: str,
    ) -> Optional[KnowledgePack]:
        """
        Automatically determine the most relevant knowledge pack for a query.
        
        Args:
            query: Search query
        
        Returns:
            Most relevant knowledge pack
        """
        query_lower = query.lower()
        
        # Score each pack based on query relevance
        pack_scores = {}
        
        for pack in self.packs.values():
            score = 0
            
            # Check if query matches pack type keywords
            if pack.pack_type == KnowledgePackType.EDUCATION:
                education_keywords = ["teach", "learn", "study", "exam", "homework", "formula"]
                if any(kw in query_lower for kw in education_keywords):
                    score += 2
            
            elif pack.pack_type == KnowledgePackType.MEDICAL:
                medical_keywords = ["medical", "health", "symptom", "diagnosis", "treatment"]
                if any(kw in query_lower for kw in medical_keywords):
                    score += 2
            
            elif pack.pack_type == KnowledgePackType.PROGRAMMING:
                programming_keywords = ["code", "programming", "software", "debug", "api"]
                if any(kw in query_lower for kw in programming_keywords):
                    score += 2
            
            elif pack.pack_type == KnowledgePackType.TRADING:
                trading_keywords = ["trade", "stock", "market", "invest", "chart"]
                if any(kw in query_lower for kw in trading_keywords):
                    score += 2
            
            # Check if query matches pack content
            pack_results = pack.search_knowledge(query, limit=5)
            score += len(pack_results)
            
            pack_scores[pack.pack_id] = score
        
        # Return pack with highest score
        if pack_scores:
            best_pack_id = max(pack_scores, key=pack_scores.get)
            if pack_scores[best_pack_id] > 0:
                return self.packs[best_pack_id]
        
        return None
    
    def format_answer_with_template(
        self,
        pack_id: str,
        answer: str,
    ) -> str:
        """
        Format an answer using the pack's answer template.
        
        Args:
            pack_id: ID of the knowledge pack
            answer: The answer to format
        
        Returns:
            Formatted answer
        """
        pack = self.get_pack(pack_id)
        if not pack or not pack.answer_template:
            return answer
        
        return pack.answer_template.format(answer=answer)
    
    def get_pack_statistics(self) -> Dict[str, Any]:
        """Get statistics about all knowledge packs"""
        if not self.packs:
            return {
                "total_packs": 0,
                "by_type": {},
                "total_items": 0,
            }
        
        by_type = {}
        total_items = 0
        
        for pack in self.packs.values():
            pack_type = pack.pack_type.value
            by_type[pack_type] = by_type.get(pack_type, 0) + 1
            total_items += len(pack.knowledge_items)
        
        return {
            "total_packs": len(self.packs),
            "by_type": by_type,
            "total_items": total_items,
            "average_items_per_pack": total_items / len(self.packs),
        }
