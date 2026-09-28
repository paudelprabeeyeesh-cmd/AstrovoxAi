from .base import ArchitectureRegistry, BaseArchitecture, ArchitectureSpec
from .gpt2 import GPT2Architecture
from .llama import LlamaArchitecture
from .mistral import MistralArchitecture

ArchitectureRegistry.register("gpt2", GPT2Architecture())
ArchitectureRegistry.register("llama", LlamaArchitecture())
ArchitectureRegistry.register("mistral", MistralArchitecture())

__all__ = ["ArchitectureRegistry", "BaseArchitecture", "ArchitectureSpec", "GPT2Architecture", "LlamaArchitecture", "MistralArchitecture"]
