"""
Expert Base System - Phase 4.3

Provides the foundation for all Expert AI Systems with:
- Expert profiles with domain-specific configurations
- Specialized terminology
- Curated knowledge sources
- Domain-specific tools
- Memory preferences
- Output templates
- Confidence indicators
- Safety policies
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class ExpertCategory(Enum):
    """Categories of expert systems"""
    EDUCATION = "education"
    MEDICAL = "medical"
    PROGRAMMING = "programming"
    TRADING = "trading"
    CYBERSECURITY = "cybersecurity"
    LEGAL = "legal"
    BUSINESS = "business"
    RESEARCH = "research"
    CREATIVE = "creative"
    LANGUAGE = "language"
    ENGINEERING = "engineering"
    DATA_SCIENCE = "data_science"
    PRODUCTIVITY = "productivity"


@dataclass
class ExpertCapabilities:
    """Capabilities of an expert system"""
    primary_domains: List[str] = field(default_factory=list)
    supported_languages: List[str] = field(default_factory=list)
    supported_frameworks: List[str] = field(default_factory=list)
    specialized_tools: List[str] = field(default_factory=list)
    knowledge_sources: List[str] = field(default_factory=list)
    output_formats: List[str] = field(default_factory=list)
    max_context_length: int = 4096
    supports_streaming: bool = True
    supports_multimodal: bool = False


@dataclass
class ExpertProfile:
    """Profile configuration for an expert system"""
    expert_id: str
    name: str
    category: ExpertCategory
    description: str
    system_prompt: str
    capabilities: ExpertCapabilities
    terminology: Dict[str, str] = field(default_factory=dict)
    safety_policies: List[str] = field(default_factory=list)
    confidence_threshold: float = 0.7
    requires_disclaimer: bool = False
    disclaimer_text: Optional[str] = None
    jurisdiction_aware: bool = False
    supported_jurisdictions: List[str] = field(default_factory=list)
    preferred_model: Optional[str] = None
    memory_preferences: Dict[str, Any] = field(default_factory=dict)
    output_template: Optional[str] = None


class ExpertBase:
    """
    Base class for all Expert AI Systems.
    Provides common functionality and enforces expert profile compliance.
    """
    
    def __init__(self, profile: ExpertProfile):
        self.profile = profile
        self.usage_count = 0
        self.created_at = datetime.utcnow()
        self.last_used = None
    
    def process_request(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process a request using this expert's specialized capabilities.
        
        Args:
            user_message: User's message
            context: Additional context
            user_id: User ID
        
        Returns:
            Expert response with metadata
        """
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        
        # Apply safety checks
        safety_check = self._check_safety(user_message)
        if not safety_check["safe"]:
            return {
                "success": False,
                "error": safety_check["reason"],
                "requires_intervention": True,
            }
        
        # Build expert-specific prompt
        expert_prompt = self._build_expert_prompt(user_message, context)
        
        # Process using expert's specialized logic
        response = self._generate_response(expert_prompt, context)
        
        # Add disclaimer if required
        if self.profile.requires_disclaimer and self.profile.disclaimer_text:
            response = self._add_disclaimer(response)
        
        # Calculate confidence
        confidence = self._calculate_confidence(response, user_message)
        
        return {
            "success": True,
            "expert_id": self.profile.expert_id,
            "expert_name": self.profile.name,
            "response": response,
            "confidence": confidence,
            "confidence_above_threshold": confidence >= self.profile.confidence_threshold,
            "requires_disclaimer": self.profile.requires_disclaimer,
            "metadata": {
                "usage_count": self.usage_count,
                "category": self.profile.category.value,
                "capabilities": self.profile.capabilities.__dict__,
            },
        }
    
    def _check_safety(self, message: str) -> Dict[str, Any]:
        """Check if the message violates safety policies"""
        message_lower = message.lower()
        
        for policy in self.profile.safety_policies:
            if policy.lower() in message_lower:
                return {
                    "safe": False,
                    "reason": f"Message violates safety policy: {policy}",
                }
        
        return {"safe": True}
    
    def _build_expert_prompt(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build an expert-specific prompt"""
        prompt_parts = [
            self.profile.system_prompt,
            "",
            "Specialized Instructions:",
            "- Use domain-specific terminology appropriately.",
            "- Apply expert knowledge and best practices.",
            "- Provide accurate, well-reasoned responses.",
            "",
        ]
        
        # Add terminology if available
        if self.profile.terminology:
            prompt_parts.append("Key Terminology:")
            for term, definition in self.profile.terminology.items():
                prompt_parts.append(f"- {term}: {definition}")
            prompt_parts.append("")
        
        # Add context if available
        if context:
            prompt_parts.append("Context:")
            prompt_parts.append(str(context))
            prompt_parts.append("")
        
        prompt_parts.append("User Request:")
        prompt_parts.append(user_message)
        
        return "\n".join(prompt_parts)
    
    def _generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate response (to be implemented by specific experts).
        This is a placeholder that should be overridden.
        """
        # In production, this would call the LLM with the expert's preferred model
        return f"[{self.profile.name} Response] This is a placeholder response. In production, this would be generated by the LLM using the expert's specialized system prompt and knowledge."
    
    def _add_disclaimer(self, response: str) -> str:
        """Add disclaimer to response"""
        disclaimer = f"\n\n---\n{self.profile.disclaimer_text}"
        return response + disclaimer
    
    def _calculate_confidence(
        self,
        response: str,
        user_message: str,
    ) -> float:
        """Calculate confidence in the response"""
        # This is a simplified confidence calculation
        # In production, this would use more sophisticated methods
        
        # Check for uncertainty indicators
        uncertainty_phrases = [
            "i'm not sure", "uncertain", "might be", "possibly",
            "i don't have enough information", "cannot determine",
        ]
        
        response_lower = response.lower()
        for phrase in uncertainty_phrases:
            if phrase in response_lower:
                return 0.5
        
        # Default confidence based on response quality
        if len(response) > 100:
            return 0.8
        else:
            return 0.6
    
    def get_profile(self) -> ExpertProfile:
        """Get the expert's profile"""
        return self.profile
    
    def get_capabilities(self) -> ExpertCapabilities:
        """Get the expert's capabilities"""
        return self.profile.capabilities
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "expert_id": self.profile.expert_id,
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }
    
    def update_profile(self, **kwargs):
        """Update the expert's profile"""
        for key, value in kwargs.items():
            if hasattr(self.profile, key):
                setattr(self.profile, key, value)
    
    def add_terminology(self, term: str, definition: str):
        """Add terminology to the expert"""
        self.profile.terminology[term] = definition
    
    def add_safety_policy(self, policy: str):
        """Add a safety policy"""
        if policy not in self.profile.safety_policies:
            self.profile.safety_policies.append(policy)
    
    def is_capable(self, task: str) -> bool:
        """Check if the expert is capable of handling a task"""
        task_lower = task.lower()
        
        # Check against primary domains
        for domain in self.profile.capabilities.primary_domains:
            if domain.lower() in task_lower:
                return True
        
        return False
    
    def get_recommended_model(self) -> str:
        """Get the recommended model for this expert"""
        return self.profile.preferred_model or "gpt-4"
