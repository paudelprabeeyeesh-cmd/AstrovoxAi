"""AI research package."""
from .tree_of_thought import TreeOfThought
from .graph_of_thought import GraphOfThought
from .reflection_reasoning import ReflectionReasoning
from .multi_agent_debate import MultiAgentDebate
from .adaptive_retrieval import AdaptiveRetrieval, DynamicModelRouter
from .self_improving_prompts import SelfImprovingPromptOptimizer
from .hallucination_pipeline import HallucinationReductionPipeline, AutomaticBenchmarkGenerator
from .long_context import ContextWindow

__all__ = ["TreeOfThought", "GraphOfThought", "ReflectionReasoning", "MultiAgentDebate", "AdaptiveRetrieval", "DynamicModelRouter", "SelfImprovingPromptOptimizer", "HallucinationReductionPipeline", "AutomaticBenchmarkGenerator", "ContextWindow"]
