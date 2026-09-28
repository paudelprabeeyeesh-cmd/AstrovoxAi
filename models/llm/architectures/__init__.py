from .base import ArchitectureRegistry, ArchitectureSpec, BaseArchitecture
from .deepseek import DeepSeekArchitecture
from .gemma import GemmaArchitecture
from .gpt2 import GPT2Architecture
from .llama import LlamaArchitecture
from .mistral import MistralArchitecture
from .phi import PhiArchitecture
from .qwen import QwenArchitecture

ArchitectureRegistry.register("gpt2", GPT2Architecture())
ArchitectureRegistry.register("llama", LlamaArchitecture())
ArchitectureRegistry.register("mistral", MistralArchitecture())
ArchitectureRegistry.register("gemma", GemmaArchitecture())
ArchitectureRegistry.register("qwen", QwenArchitecture())
ArchitectureRegistry.register("phi", PhiArchitecture())
ArchitectureRegistry.register("deepseek", DeepSeekArchitecture())

__all__ = [
    "ArchitectureRegistry",
    "BaseArchitecture",
    "ArchitectureSpec",
    "GPT2Architecture",
    "LlamaArchitecture",
    "MistralArchitecture",
    "GemmaArchitecture",
    "QwenArchitecture",
    "PhiArchitecture",
    "DeepSeekArchitecture",
]
