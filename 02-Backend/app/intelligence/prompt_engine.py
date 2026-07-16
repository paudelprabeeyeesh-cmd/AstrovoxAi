"""
Prompt Engine - Phase 2.3

Constructs optimized prompts through a pipeline that includes:
- Intent detection
- Memory retrieval
- Workspace context
- Knowledge search
- Tool selection
- Safety validation
- Prompt building
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class Intent(Enum):
    """Detected user intents"""
    GENERAL_CHAT = "general_chat"
    CODING = "coding"
    MATHEMATICS = "mathematics"
    RESEARCH = "research"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    IMAGE_GENERATION = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    AUTOMATION = "automation"
    SCHEDULING = "scheduling"
    EMAIL_WRITING = "email_writing"
    DEBUGGING = "debugging"
    BRAINSTORMING = "brainstorming"
    QUESTION_ANSWERING = "question_answering"


class ContextSource:
    """Represents a source of context"""
    
    def __init__(
        self,
        source_type: str,
        content: str,
        relevance_score: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.source_type = source_type
        self.content = content
        self.relevance_score = relevance_score
        self.metadata = metadata or {}


class PromptEngine:
    """
    Constructs optimized prompts by assembling relevant context
    and applying intent-specific transformations.
    """
    
    def __init__(self):
        self.intent_patterns = self._initialize_intent_patterns()
        self.system_prompts = self._initialize_system_prompts()
    
    def _initialize_intent_patterns(self) -> Dict[Intent, List[str]]:
        """Initialize keyword patterns for intent detection"""
        return {
            Intent.CODING: [
                "code", "function", "class", "debug", "fix", "implement",
                "programming", "python", "javascript", "api", "algorithm",
                "write a function", "create a script", "help me code",
            ],
            Intent.MATHEMATICS: [
                "calculate", "solve", "equation", "math", "formula",
                "compute", "statistics", "probability", "derivative",
                "integral", "algebra", "geometry",
            ],
            Intent.RESEARCH: [
                "research", "find information", "look up", "investigate",
                "tell me about", "what is", "explain", "analyze",
                "compare", "history of",
            ],
            Intent.TRANSLATION: [
                "translate", "translation", "in spanish", "in french",
                "in german", "in nepali", "in japanese", "in chinese",
                "to english", "to spanish",
            ],
            Intent.SUMMARIZATION: [
                "summarize", "summary", "brief", "condense", "shorten",
                "give me the gist", "key points", "main idea",
            ],
            Intent.DOCUMENT_ANALYSIS: [
                "analyze this document", "read this pdf", "extract from",
                "parse this", "document", "file", "attachment",
            ],
            Intent.AUTOMATION: [
                "automate", "script", "workflow", "batch", "schedule",
                "trigger", "automation", "bot",
            ],
            Intent.SCHEDULING: [
                "schedule", "calendar", "appointment", "meeting", "reminder",
                "set up", "book", "reserve",
            ],
            Intent.EMAIL_WRITING: [
                "write an email", "draft email", "email template", "compose",
                "reply to", "email to",
            ],
            Intent.DEBUGGING: [
                "debug", "error", "bug", "fix error", "troubleshoot",
                "not working", "broken", "issue",
            ],
            Intent.BRAINSTORMING: [
                "brainstorm", "ideas", "suggest", "creative", "think of",
                "come up with", "list", "options",
            ],
            Intent.QUESTION_ANSWERING: [
                "what", "how", "why", "when", "where", "who", "which",
                "can you tell me", "do you know",
            ],
        }
    
    def _initialize_system_prompts(self) -> Dict[Intent, str]:
        """Initialize system prompts for different intents"""
        return {
            Intent.CODING: """You are an expert software developer and coding assistant. 
Provide clean, well-documented code with best practices. Include explanations when helpful.
Consider edge cases, error handling, and performance optimization.""",
            
            Intent.MATHEMATICS: """You are a mathematical expert. Provide clear, step-by-step solutions.
Show your work and explain the reasoning behind each step.""",
            
            Intent.RESEARCH: """You are a research assistant. Provide accurate, well-sourced information.
Distinguish between facts and opinions. Mention uncertainties when present.""",
            
            Intent.TRANSLATION: """You are a professional translator. Provide accurate translations
that capture the meaning and tone of the original text. Consider cultural context.""",
            
            Intent.SUMMARIZATION: """You are a skilled summarizer. Extract key information and
present it concisely while maintaining accuracy and important details.""",
            
            Intent.DOCUMENT_ANALYSIS: """You are a document analysis expert. Extract and organize
information from documents. Identify key themes, entities, and relationships.""",
            
            Intent.AUTOMATION: """You are an automation specialist. Design efficient, reliable
automation solutions. Consider error handling, logging, and maintainability.""",
            
            Intent.SCHEDULING: """You are a scheduling assistant. Help organize time effectively.
Consider priorities, conflicts, and optimal timing.""",
            
            Intent.EMAIL_WRITING: """You are a professional communication expert. Write clear,
concise, and appropriate emails. Consider tone, audience, and purpose.""",
            
            Intent.DEBUGGING: """You are a debugging expert. Systematically identify issues,
explain root causes, and provide solutions. Consider edge cases and error scenarios.""",
            
            Intent.BRAINSTORMING: """You are a creative brainstorming partner. Generate diverse,
innovative ideas. Build upon concepts and explore possibilities.""",
            
            Intent.QUESTION_ANSWERING: """You are a knowledgeable assistant. Provide accurate,
helpful answers. If uncertain, acknowledge limitations and suggest where to find more information.""",
            
            Intent.GENERAL_CHAT: """You are Astrovox, an intelligent AI assistant. Be helpful,
accurate, and engaging in conversation.""",
        }
    
    def detect_intent(self, message: str, context: Optional[Dict[str, Any]] = None) -> Intent:
        """
        Detect the user's intent from their message.
        
        Args:
            message: The user's message
            context: Additional context (files, conversation history, etc.)
        
        Returns:
            Detected Intent
        """
        message_lower = message.lower()
        scores = {}
        
        # Score each intent based on keyword matches
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                scores[intent] = score
        
        # Check context for additional signals
        if context:
            if context.get("has_document"):
                scores[Intent.DOCUMENT_ANALYSIS] = scores.get(Intent.DOCUMENT_ANALYSIS, 0) + 3
            if context.get("has_code"):
                scores[Intent.CODING] = scores.get(Intent.CODING, 0) + 2
            if context.get("has_image"):
                scores[Intent.IMAGE_ANALYSIS] = scores.get(Intent.IMAGE_ANALYSIS, 0) + 3
        
        # Return highest scoring intent, or default to general chat
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return Intent.GENERAL_CHAT
    
    def assemble_context(
        self,
        user_id: int,
        conversation_id: Optional[int],
        message: str,
        context_sources: Optional[List[ContextSource]] = None,
        max_context_length: int = 4000,
    ) -> List[ContextSource]:
        """
        Assemble relevant context from multiple sources.
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            message: Current message
            context_sources: Additional context sources
            max_context_length: Maximum total context length
        
        Returns:
            List of context sources sorted by relevance
        """
        all_sources = context_sources or []
        
        # In a real implementation, this would:
        # 1. Retrieve conversation history
        # 2. Retrieve relevant long-term memory
        # 3. Search knowledge base
        # 4. Include workspace data
        # 5. Include uploaded files
        
        # For now, we'll return the provided sources
        # Sort by relevance score
        all_sources.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Trim to fit within max length
        total_length = 0
        trimmed_sources = []
        
        for source in all_sources:
            if total_length + len(source.content) <= max_context_length:
                trimmed_sources.append(source)
                total_length += len(source.content)
        
        return trimmed_sources
    
    def select_tools(self, intent: Intent, message: str) -> List[str]:
        """
        Select appropriate tools based on intent and message.
        
        Args:
            intent: Detected intent
            message: User message
        
        Returns:
            List of tool names to make available
        """
        tool_mapping = {
            Intent.CODING: ["code_executor", "python_sandbox", "github"],
            Intent.MATHEMATICS: ["calculator"],
            Intent.RESEARCH: ["web_search", "wikipedia"],
            Intent.TRANSLATION: [],  # Model handles translation
            Intent.SUMMARIZATION: [],
            Intent.DOCUMENT_ANALYSIS: ["pdf_reader", "ocr", "file_reader"],
            Intent.AUTOMATION: ["browser_automation", "api_call"],
            Intent.SCHEDULING: ["calendar"],
            Intent.EMAIL_WRITING: ["email"],
            Intent.DEBUGGING: ["code_executor", "python_sandbox"],
            Intent.BRAINSTORMING: [],
            Intent.QUESTION_ANSWERING: ["web_search"],
            Intent.GENERAL_CHAT: ["web_search"],
        }
        
        return tool_mapping.get(intent, [])
    
    def validate_safety(self, prompt: str) -> tuple[bool, Optional[str]]:
        """
        Validate the prompt for safety concerns.
        
        Args:
            prompt: The constructed prompt
        
        Returns:
            (is_safe, reason_if_unsafe)
        """
        # Basic safety checks
        dangerous_patterns = [
            "ignore previous instructions",
            "override safety",
            "bypass security",
            "exploit",
            "hack into",
            "generate malware",
            "create virus",
        ]
        
        prompt_lower = prompt.lower()
        for pattern in dangerous_patterns:
            if pattern in prompt_lower:
                return False, f"Potentially unsafe pattern detected: {pattern}"
        
        return True, None
    
    def build_prompt(
        self,
        user_message: str,
        intent: Intent,
        context_sources: List[ContextSource],
        available_tools: List[str],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the final prompt with all components.
        
        Args:
            user_message: The user's message
            intent: Detected intent
            context_sources: Relevant context sources
            available_tools: Tools available for this request
            conversation_history: Previous conversation messages
            user_preferences: User-specific preferences
        
        Returns:
            Constructed prompt dictionary
        """
        # Get system prompt for this intent
        system_prompt = self.system_prompts.get(intent, self.system_prompts[Intent.GENERAL_CHAT])
        
        # Build context section
        context_sections = []
        for source in context_sources:
            if source.relevance_score > 0.5:  # Only include relevant context
                context_sections.append(
                    f"[{source.source_type}]: {source.content}"
                )
        
        context_text = "\n\n".join(context_sections) if context_sections else "No additional context."
        
        # Build tools section
        tools_text = ""
        if available_tools:
            tools_text = f"\n\nAvailable tools: {', '.join(available_tools)}"
        
        # Build conversation history
        history_text = ""
        if conversation_history:
            history_messages = [
                f"{msg['role']}: {msg['content']}"
                for msg in conversation_history[-5:]  # Last 5 messages
            ]
            history_text = "\n\nConversation history:\n" + "\n".join(history_messages)
        
        # Apply user preferences
        if user_preferences:
            if user_preferences.get("response_style") == "concise":
                system_prompt += "\n\nKeep responses concise and to the point."
            elif user_preferences.get("response_style") == "detailed":
                system_prompt += "\n\nProvide detailed, comprehensive responses."
            
            if user_preferences.get("language"):
                system_prompt += f"\n\nRespond in {user_preferences['language']}."
        
        # Construct full prompt
        full_prompt = f"""{system_prompt}

Context information:
{context_text}
{tools_text}
{history_text}

User message: {user_message}"""
        
        # Validate safety
        is_safe, safety_reason = self.validate_safety(full_prompt)
        if not is_safe:
            return {
                "error": "Safety validation failed",
                "reason": safety_reason,
                "is_safe": False,
            }
        
        return {
            "system_prompt": system_prompt,
            "context": context_text,
            "tools": available_tools,
            "conversation_history": history_text,
            "user_message": user_message,
            "full_prompt": full_prompt,
            "intent": intent.value,
            "is_safe": True,
        }
    
    def construct_prompt(
        self,
        user_id: int,
        user_message: str,
        conversation_id: Optional[int] = None,
        context_sources: Optional[List[ContextSource]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for prompt construction.
        
        Args:
            user_id: User ID
            user_message: User's message
            conversation_id: Conversation ID
            context_sources: Additional context sources
            conversation_history: Conversation history
            user_preferences: User preferences
        
        Returns:
            Constructed prompt with metadata
        """
        # Detect intent
        intent = self.detect_intent(user_message)
        
        # Assemble context
        context = self.assemble_context(
            user_id, conversation_id, user_message, context_sources
        )
        
        # Select tools
        tools = self.select_tools(intent, user_message)
        
        # Build prompt
        prompt = self.build_prompt(
            user_message, intent, context, tools, conversation_history, user_preferences
        )
        
        return prompt
