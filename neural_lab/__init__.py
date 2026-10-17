"""Experimental CPU-first Neural Lab with deferred heavy PyTorch imports."""

from importlib import import_module

__all__ = [
    "CharacterTokenizer", "DatasetStore", "MemoryEstimate", "ModelRegistry", "TinyTransformer",
    "TinyTransformerConfig", "MultilayerPerceptron", "enforce_memory_budget", "estimate_training_memory",
    "evaluate_checkpoint", "generate_text", "list_experiments", "load_experimental_checkpoint",
]

_EXPORTS = {
    "CharacterTokenizer": ("tokenizer", "CharacterTokenizer"),
    "DatasetStore": ("datasets", "DatasetStore"),
    "MemoryEstimate": ("resources", "MemoryEstimate"),
    "ModelRegistry": ("registry", "ModelRegistry"),
    "TinyTransformer": ("model", "TinyTransformer"),
    "MultilayerPerceptron": ("mlp", "MultilayerPerceptron"),
    "TinyTransformerConfig": ("config", "TinyTransformerConfig"),
    "enforce_memory_budget": ("resources", "enforce_memory_budget"),
    "estimate_training_memory": ("resources", "estimate_training_memory"),
    "evaluate_checkpoint": ("evaluation", "evaluate_checkpoint"),
    "generate_text": ("evaluation", "generate_text"),
    "list_experiments": ("experiments", "list_experiments"),
    "load_experimental_checkpoint": ("evaluation", "load_experimental_checkpoint"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = _EXPORTS[name]
    value = getattr(import_module(f".{module_name}", __name__), attribute)
    globals()[name] = value
    return value
