"""
Model Orchestrator - Phase 2.2

Intelligently routes requests to the most suitable AI model based on:
- Task type (coding, math, vision, translation, etc.)
- Cost optimization
- Latency requirements
- Context size needs
- User preferences
- Model availability
- Fallback chains
"""

import os
from typing import Dict, List, Optional, Any
from enum import Enum


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    QWEN = "qwen"
    LLAMA = "llama"
    OLLAMA = "ollama"


class TaskType(str, Enum):
    GENERAL_CHAT = "general_chat"
    CODING = "coding"
    MATHEMATICS = "mathematics"
    VISION = "vision"
    TRANSLATION = "translation"
    RESEARCH = "research"
    SUMMARIZATION = "summarization"
    IMAGE_GENERATION = "image_generation"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    DEBUGGING = "debugging"
    BRAINSTORMING = "brainstorming"


class ModelConfig:
    def __init__(
        self,
        provider: ModelProvider,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: int = 4096,
        cost_per_1k_input: float = 0.0,
        cost_per_1k_output: float = 0.0,
        avg_latency_ms: int = 1000,
        supports_vision: bool = False,
        supports_function_calling: bool = True,
        preferred_tasks: List[TaskType] = None,
        fallback_chain: Optional[List[str]] = None,
    ):
        self.provider = provider
        self.model_name = model_name
        self.api_key = api_key or os.getenv(f"{provider.value.upper()}_API_KEY")
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self.avg_latency_ms = avg_latency_ms
        self.supports_vision = supports_vision
        self.supports_function_calling = supports_function_calling
        self.preferred_tasks = preferred_tasks or []
        self.fallback_chain = fallback_chain or []


class ModelOrchestrator:
    def __init__(self):
        self.models: Dict[str, ModelConfig] = {}
        self.task_routing: Dict[TaskType, List[str]] = {}
        self.user_preferences: Dict[int, str] = {}
        self._initialize_default_models()
        self._initialize_task_routing()

    def _initialize_default_models(self):
        self.models["gpt-4"] = ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4",
            max_tokens=8192,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            avg_latency_ms=2000,
            supports_function_calling=True,
            preferred_tasks=[TaskType.CODING, TaskType.MATHEMATICS, TaskType.GENERAL_CHAT],
            fallback_chain=["gpt-4-turbo", "claude-3-sonnet"],
        )
        self.models["gpt-4-turbo"] = ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4-turbo-preview",
            max_tokens=128000,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
            avg_latency_ms=1500,
            supports_function_calling=True,
            preferred_tasks=[TaskType.CODING, TaskType.DOCUMENT_ANALYSIS, TaskType.RESEARCH],
            fallback_chain=["gpt-4", "gpt-3.5-turbo"],
        )
        self.models["gpt-3.5-turbo"] = ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-3.5-turbo",
            max_tokens=16385,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            avg_latency_ms=500,
            supports_function_calling=True,
            preferred_tasks=[TaskType.GENERAL_CHAT, TaskType.TRANSLATION],
            fallback_chain=["gemini-pro"],
        )
        self.models["claude-3-opus"] = ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-opus-20240229",
            max_tokens=200000,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            avg_latency_ms=2500,
            supports_function_calling=True,
            preferred_tasks=[TaskType.CODING, TaskType.RESEARCH, TaskType.DOCUMENT_ANALYSIS],
            fallback_chain=["claude-3-sonnet", "gpt-4-turbo"],
        )
        self.models["claude-3-sonnet"] = ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_name="claude-3-sonnet-20240229",
            max_tokens=200000,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            avg_latency_ms=1000,
            supports_function_calling=True,
            preferred_tasks=[TaskType.CODING, TaskType.GENERAL_CHAT, TaskType.SUMMARIZATION],
            fallback_chain=["gpt-3.5-turbo", "gemini-pro"],
        )
        self.models["gemini-pro"] = ModelConfig(
            provider=ModelProvider.GOOGLE,
            model_name="gemini-pro",
            max_tokens=91728,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
            avg_latency_ms=800,
            supports_function_calling=True,
            preferred_tasks=[TaskType.TRANSLATION, TaskType.GENERAL_CHAT],
            fallback_chain=["gpt-3.5-turbo"],
        )
        self.models["llama2"] = ModelConfig(
            provider=ModelProvider.OLLAMA,
            model_name="llama2",
            base_url="http://localhost:11434",
            max_tokens=4096,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
            avg_latency_ms=3000,
            supports_function_calling=False,
            preferred_tasks=[TaskType.GENERAL_CHAT],
            fallback_chain=[],
        )

    def _initialize_task_routing(self):
        self.task_routing = {
            TaskType.CODING: ["claude-3-opus", "gpt-4-turbo", "gpt-4"],
            TaskType.MATHEMATICS: ["gpt-4", "claude-3-opus"],
            TaskType.VISION: ["gpt-4-vision-preview", "claude-3-opus"],
            TaskType.TRANSLATION: ["gemini-pro", "gpt-3.5-turbo"],
            TaskType.RESEARCH: ["claude-3-opus", "gpt-4-turbo"],
            TaskType.SUMMARIZATION: ["claude-3-sonnet", "gpt-3.5-turbo"],
            TaskType.DOCUMENT_ANALYSIS: ["claude-3-opus", "gpt-4-turbo"],
            TaskType.DEBUGGING: ["claude-3-opus", "gpt-4"],
            TaskType.BRAINSTORMING: ["claude-3-sonnet", "gpt-4"],
            TaskType.GENERAL_CHAT: ["gpt-3.5-turbo", "claude-3-sonnet", "gemini-pro"],
        }

    def register_model(self, model_id: str, config: ModelConfig):
        self.models[model_id] = config

    def set_user_preference(self, user_id: int, model_name: str):
        if model_name in self.models:
            self.user_preferences[user_id] = model_name

    def detect_task_type(self, message: str, context: Dict[str, Any] = None) -> TaskType:
        message_lower = message.lower()
        coding_keywords = ["code", "function", "class", "debug", "fix", "implement", "programming", "python", "javascript", "api"]
        if any(keyword in message_lower for keyword in coding_keywords):
            return TaskType.CODING
        math_keywords = ["calculate", "solve", "equation", "math", "formula", "compute", "statistics"]
        if any(keyword in message_lower for keyword in math_keywords):
            return TaskType.MATHEMATICS
        translation_keywords = ["translate", "translation", "in spanish", "in french", "in german", "in nepali"]
        if any(keyword in message_lower for keyword in translation_keywords):
            return TaskType.TRANSLATION
        research_keywords = ["research", "find information", "look up", "investigate", "analyze"]
        if any(keyword in message_lower for keyword in research_keywords):
            return TaskType.RESEARCH
        summary_keywords = ["summarize", "summary", "brief", "condense"]
        if any(keyword in message_lower for keyword in summary_keywords):
            return TaskType.SUMMARIZATION
        if context and context.get("has_document"):
            return TaskType.DOCUMENT_ANALYSIS
        return TaskType.GENERAL_CHAT

    def select_model(
        self,
        task_type: TaskType,
        user_id: Optional[int] = None,
        optimize_for: str = "balanced",
        max_tokens: Optional[int] = None,
        requires_vision: bool = False,
        requires_function_calling: bool = True,
    ) -> Optional[ModelConfig]:
        if user_id and user_id in self.user_preferences:
            preferred_model = self.models.get(self.user_preferences[user_id])
            if preferred_model and self._meets_requirements(
                preferred_model, max_tokens, requires_vision, requires_function_calling
            ):
                return preferred_model

        candidates = self.task_routing.get(task_type, list(self.models.keys()))
        suitable_models = []
        for model_id in candidates:
            if model_id not in self.models:
                continue
            model = self.models[model_id]
            if self._meets_requirements(model, max_tokens, requires_vision, requires_function_calling):
                suitable_models.append(model)

        if not suitable_models:
            for model in self.models.values():
                if self._meets_requirements(model, max_tokens, requires_vision, requires_function_calling):
                    suitable_models.append(model)

        if not suitable_models:
            return None

        if optimize_for == "cost":
            suitable_models.sort(key=lambda m: m.cost_per_1k_input + m.cost_per_1k_output)
        elif optimize_for == "speed":
            suitable_models.sort(key=lambda m: m.avg_latency_ms)
        elif optimize_for == "quality":
            suitable_models.sort(key=lambda m: m.max_tokens, reverse=True)
        else:
            suitable_models.sort(
                key=lambda m: (
                    m.cost_per_1k_input + m.cost_per_1k_output,
                    m.avg_latency_ms,
                    -m.max_tokens,
                )
            )
        return suitable_models[0]

    def _meets_requirements(
        self,
        model: ModelConfig,
        max_tokens: Optional[int],
        requires_vision: bool,
        requires_function_calling: bool,
    ) -> bool:
        if max_tokens and model.max_tokens < max_tokens:
            return False
        if requires_vision and not model.supports_vision:
            return False
        if requires_function_calling and not model.supports_function_calling:
            return False
        return True

    def estimate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        model = self.models.get(model_name)
        if not model:
            return 0.0
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output
        return input_cost + output_cost

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        model = self.models.get(model_name)
        if not model:
            return None
        return {
            "provider": model.provider.value,
            "model_name": model.model_name,
            "max_tokens": model.max_tokens,
            "cost_per_1k_input": model.cost_per_1k_input,
            "cost_per_1k_output": model.cost_per_1k_output,
            "avg_latency_ms": model.avg_latency_ms,
            "supports_vision": model.supports_vision,
            "supports_function_calling": model.supports_function_calling,
            "preferred_tasks": [t.value for t in model.preferred_tasks],
            "fallback_chain": model.fallback_chain,
        }

    def list_available_models(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": model_id,
                **self.get_model_info(model_id),
            }
            for model_id in self.models.keys()
        ]
