"""
Universal AI Router - Phase 4.2

Automatically routes requests to the appropriate Expert AI based on:
- Intent detection
- Domain analysis
- Content analysis
- User preferences
- Task complexity

Supports both automatic routing (Mode A) and manual selection (Mode B).
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

from .expert_base import ExpertBase, ExpertProfile, ExpertCategory


class RoutingMode(Enum):
    """Routing modes"""
    AUTOMATIC = "automatic"  # Mode A: Automatic AI
    MANUAL = "manual"  # Mode B: Manual Expert Selection


@dataclass
class RoutingDecision:
    """Result of routing decision"""
    selected_expert_id: str
    selected_expert_name: str
    confidence: float
    reasoning: str
    alternative_experts: List[str]
    requires_collaboration: bool = False
    collaboration_partners: List[str] = None


class UniversalRouter:
    """
    Routes user requests to the most appropriate Expert AI.
    Acts as the Universal AI that coordinates between expert systems.
    """
    
    def __init__(self):
        self.experts: Dict[str, ExpertBase] = {}
        self.routing_rules: Dict[str, str] = {}
        self.user_preferences: Dict[int, str] = {}  # user_id -> expert_id
        self.routing_history: List[Dict[str, Any]] = []
    
    def register_expert(self, expert: ExpertBase):
        """Register an expert system"""
        self.experts[expert.profile.expert_id] = expert
    
    def set_user_preference(self, user_id: int, expert_id: str):
        """Set user's preferred expert"""
        if expert_id in self.experts:
            self.user_preferences[user_id] = expert_id
    
    def route_request(
        self,
        user_message: str,
        user_id: Optional[int] = None,
        mode: RoutingMode = RoutingMode.AUTOMATIC,
        context: Optional[Dict[str, Any]] = None,
    ) -> RoutingDecision:
        """
        Route a request to the the appropriate expert.
        
        Args:
            user_message: User's message
            user_id: User ID
            mode: Routing mode (automatic or manual)
            context: Additional context
        
        Returns:
            Routing decision with selected expert
        """
        # Check for manual mode with user preference
        if mode == RoutingMode.MANUAL and user_id and user_id in self.user_preferences:
            preferred_expert_id = self.user_preferences[user_id]
            if preferred_expert_id in self.experts:
                return self._create_decision(
                    expert_id=preferred_expert_id,
                    confidence=1.0,
                    reasoning="User manually selected this expert",
                    user_preference=True,
                )
        
        # Automatic routing
        return self._automatic_route(user_message, user_id, context)
    
    def _automatic_route(
        self,
        user_message: str,
        user_id: Optional[int],
        context: Optional[Dict[str, Any]],
    ) -> RoutingDecision:
        """Perform automatic routing based on content analysis"""
        message_lower = user_message.lower()
        
        # Analyze message for domain indicators
        domain_scores = self._analyze_domain(message_lower, context)
        
        # Get highest scoring domain
        if not domain_scores:
            # Default to a general expert if no domain detected
            return self._get_default_expert()
        
        best_expert_id, score = max(domain_scores.items(), key=lambda x: x[1])
        
        # Check if collaboration is needed
        requires_collaboration, partners = self._check_collaboration_needs(
            message_lower, domain_scores
        )
        
        # Get alternatives
        alternatives = [
            expert_id for expert_id, expert_score in domain_scores.items()
            if expert_id != best_expert_id and expert_score > 0.3
        ]
        
        # Create reasoning
        reasoning = self._generate_reasoning(best_expert_id, domain_scores)
        
        decision = RoutingDecision(
            selected_expert_id=best_expert_id,
            selected_expert_name=self.experts[best_expert_id].profile.name,
            confidence=score,
            reasoning=reasoning,
            alternative_experts=alternatives,
            requires_collaboration=requires_collaboration,
            collaboration_partners=partners if requires_collaboration else None,
        )
        
        # Log routing decision
        self._log_routing(user_id, user_message, decision)
        
        return decision
    
    def _analyze_domain(
        self,
        message_lower: str,
        context: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Analyze message to determine domain scores"""
        scores = {}
        
        # Education indicators
        education_keywords = [
            "teach", "learn", "study", "homework", "exam", "quiz", "formula",
            "mathematics", "physics", "chemistry", "biology", "history",
            "explain", "what is", "how does", "why is", "solve", "calculate",
        ]
        education_score = sum(1 for kw in education_keywords if kw in message_lower)
        if education_score > 0:
            scores["education"] = min(education_score / 3.0, 1.0)
        
        # Medical indicators
        medical_keywords = [
            "symptom", "diagnosis", "treatment", "medicine", "drug", "disease",
            "anatomy", "physiology", "pharmacology", "medical", "health",
            "pain", "infection", "virus", "bacteria", "therapy",
        ]
        medical_score = sum(1 for kw in medical_keywords if kw in message_lower)
        if medical_score > 0:
            scores["medical"] = min(medical_score / 2.0, 1.0)
        
        # Programming indicators
        programming_keywords = [
            "code", "function", "class", "debug", "programming", "software",
            "algorithm", "api", "database", "framework", "library",
            "python", "javascript", "java", "react", "angular", "vue",
            "git", "github", "deploy", "build", "compile", "syntax error",
        ]
        programming_score = sum(1 for kw in programming_keywords if kw in message_lower)
        if programming_score > 0:
            scores["programming"] = min(programming_score / 2.0, 1.0)
        
        # Trading indicators
        trading_keywords = [
            "stock", "trade", "market", "invest", "portfolio", "chart",
            "technical analysis", "fundamental", "crypto", "forex", "commodity",
            "profit", "loss", "risk management", "trading strategy",
        ]
        trading_score = sum(1 for kw in trading_keywords if kw in message_lower)
        if trading_score > 0:
            scores["trading"] = min(trading_score / 2.0, 1.0)
        
        # Cybersecurity indicators
        security_keywords = [
            "hack", "security", "vulnerability", "malware", "phishing",
            "encryption", "firewall", "intrusion", "threat", "attack",
            "penetration test", "forensics", "secure coding",
        ]
        security_score = sum(1 for kw in security_keywords if kw in message_lower)
        if security_score > 0:
            scores["cybersecurity"] = min(security_score / 2.0, 1.0)
        
        # Legal indicators
        legal_keywords = [
            "law", "legal", "contract", "agreement", "compliance", "regulation",
            "jurisdiction", "lawsuit", "court", "litigation", "patent",
            "copyright", "trademark", "legal advice",
        ]
        legal_score = sum(1 for kw in legal_keywords if kw in message_lower)
        if legal_score > 0:
            scores["legal"] = min(legal_score / 2.0, 1.0)
        
        # Business indicators
        business_keywords = [
            "business", "marketing", "sales", "finance", "accounting",
            "management", "strategy", "revenue", "profit", "business plan",
            "hr", "human resources", "product", "startup",
        ]
        business_score = sum(1 for kw in business_keywords if kw in message_lower)
        if business_score > 0:
            scores["business"] = min(business_score / 3.0, 1.0)
        
        # Research indicators
        research_keywords = [
            "research", "paper", "study", "citation", "literature review",
            "hypothesis", "experiment", "data analysis", "academic",
            "journal", "publication", "peer review",
        ]
        research_score = sum(1 for kw in research_keywords if kw in message_lower)
        if research_score > 0:
            scores["research"] = min(research_score / 2.0, 1.0)
        
        # Creative indicators
        creative_keywords = [
            "write", "story", "poem", "creative", "design", "art",
            "music", "script", "brand", "logo", "creative writing",
        ]
        creative_score = sum(1 for kw in creative_keywords if kw in message_lower)
        if creative_score > 0:
            scores["creative"] = min(creative_score / 2.0, 1.0)
        
        # Language indicators
        language_keywords = [
            "translate", "translation", "grammar", "language", "speak",
            "pronunciation", "english", "spanish", "french", "german",
            "writing improvement", "proofread",
        ]
        language_score = sum(1 for kw in language_keywords if kw in message_lower)
        if language_score > 0:
            scores["language"] = min(language_score / 2.0, 1.0)
        
        # Engineering indicators
        engineering_keywords = [
            "engineering", "mechanical", "civil", "electrical", "robotics",
            "aerospace", "manufacturing", "design", "cad", "blueprint",
        ]
        engineering_score = sum(1 for kw in engineering_keywords if kw in message_lower)
        if engineering_score > 0:
            scores["engineering"] = min(engineering_score / 2.0, 1.0)
        
        # Data Science indicators
        datascience_keywords = [
            "data science", "machine learning", "deep learning", "ai",
            "neural network", "statistics", "visualization", "prediction",
            "model", "training", "dataset", "sql", "database",
        ]
        datascience_score = sum(1 for kw in datascience_keywords if kw in message_lower)
        if datascience_score > 0:
            scores["data_science"] = min(datascience_score / 2.0, 1.0)
        
        # Productivity indicators
        productivity_keywords = [
            "calendar", "schedule", "email", "task", "meeting", "note",
            "organize", "plan", "productivity", "time management",
        ]
        productivity_score = sum(1 for kw in productivity_keywords if kw in message_lower)
        if productivity_score > 0:
            scores["productivity"] = min(productivity_score / 2.0, 1.0)
        
        # Map domain names to expert IDs
        expert_mapping = {
            "education": "education_ai",
            "medical": "medical_ai",
            "programming": "programming_ai",
            "trading": "trading_ai",
            "cybersecurity": "cybersecurity_ai",
            "legal": "legal_ai",
            "business": "business_ai",
            "research": "research_ai",
            "creative": "creative_ai",
            "language": "language_ai",
            "engineering": "engineering_ai",
            "data_science": "data_science_ai",
            "productivity": "productivity_ai",
        }
        
        # Convert domain scores to expert scores
        expert_scores = {}
        for domain, score in scores.items():
            expert_id = expert_mapping.get(domain)
            if expert_id and expert_id in self.experts:
                expert_scores[expert_id] = score
        
        return expert_scores
    
    def _check_collaboration_needs(
        self,
        message_lower: str,
        domain_scores: Dict[str, float],
    ) -> tuple[bool, List[str]]:
        """Check if multiple experts should collaborate"""
        # Check for multi-domain tasks
        high_scoring_domains = [
            expert_id for expert_id, score in domain_scores.items()
            if score >= 0.5
        ]
        
        if len(high_scoring_domains) >= 2:
            return True, high_scoring_domains
        
        # Check for specific collaboration indicators
        collaboration_indicators = [
            "build a system", "create a platform", "develop an app",
            "comprehensive analysis", "multi-disciplinary",
        ]
        
        for indicator in collaboration_indicators:
            if indicator in message_lower:
                return True, list(domain_scores.keys())[:3]
        
        return False, []
    
    def _generate_reasoning(
        self,
        selected_expert_id: str,
        domain_scores: Dict[str, float],
    ) -> str:
        """Generate reasoning for routing decision"""
        expert = self.experts.get(selected_expert_id)
        if not expert:
            return "Expert not found"
        
        reasoning_parts = [
            f"Selected {expert.profile.name} based on domain analysis.",
            f"Domain match score: {domain_scores.get(selected_expert_id, 0):.2f}",
        ]
        
        # Add other detected domains
        other_domains = [
            f"{self.experts[eid].profile.name} ({score:.2f})"
            for eid, score in domain_scores.items()
            if eid != selected_expert_id and score > 0.3
        ]
        
        if other_domains:
            reasoning_parts.append(f"Other detected domains: {', '.join(other_domains)}")
        
        return " ".join(reasoning_parts)
    
    def _create_decision(
        self,
        expert_id: str,
        confidence: float,
        reasoning: str,
        user_preference: bool = False,
    ) -> RoutingDecision:
        """Create a routing decision"""
        expert = self.experts.get(expert_id)
        if not expert:
            raise ValueError(f"Expert {expert_id} not found")
        
        return RoutingDecision(
            selected_expert_id=expert_id,
            selected_expert_name=expert.profile.name,
            confidence=confidence,
            reasoning=reasoning + (" (user preference)" if user_preference else ""),
            alternative_experts=[],
        )
    
    def _get_default_expert(self) -> RoutingDecision:
        """Get default expert when no domain is detected"""
        # Try to find a general-purpose expert
        for expert_id, expert in self.experts.items():
            if "general" in expert.profile.expert_id.lower():
                return self._create_decision(
                    expert_id=expert_id,
                    confidence=0.5,
                    reasoning="No specific domain detected, using general expert",
                )
        
        # Fall back to first available expert
        if self.experts:
            first_expert_id = list(self.experts.keys())[0]
            return self._create_decision(
                expert_id=first_expert_id,
                confidence=0.3,
                reasoning="No specific domain detected, using default expert",
            )
        
        raise ValueError("No experts registered")
    
    def _log_routing(
        self,
        user_id: Optional[int],
        message: str,
        decision: RoutingDecision,
    ):
        """Log routing decision for analysis"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "message": message[:100],  # Truncate for logging
            "selected_expert": decision.selected_expert_id,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
        }
        self.routing_history.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        if not self.routing_history:
            return {"total_routes": 0}
        
        expert_counts = {}
        for entry in self.routing_history:
            expert = entry["selected_expert"]
            expert_counts[expert] = expert_counts.get(expert, 0) + 1
        
        return {
            "total_routes": len(self.routing_history),
            "expert_distribution": expert_counts,
            "registered_experts": len(self.experts),
        }
    
    def list_experts(self) -> List[Dict[str, Any]]:
        """List all registered experts"""
        return [
            {
                "expert_id": expert.profile.expert_id,
                "name": expert.profile.name,
                "category": expert.profile.category.value,
                "description": expert.profile.description,
            }
            for expert in self.experts.values()
        ]
