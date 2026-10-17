"""Validated settings for the isolated educational language model."""

from dataclasses import asdict, dataclass

MAX_VOCAB_SIZE = 4096


@dataclass(frozen=True)
class TinyTransformerConfig:
    vocab_size: int
    context_length: int = 64
    hidden_size: int = 32
    num_layers: int = 1
    num_heads: int = 2
    dropout: float = 0.0
    mlp_ratio: int = 2
    seed: int = 17
    batch_size: int = 1
    memory_budget_mib: int = 256
    reserve_memory_mib: int = 1536

    def __post_init__(self) -> None:
        for name in ("vocab_size", "context_length", "hidden_size", "num_layers", "num_heads", "mlp_ratio", "batch_size", "memory_budget_mib"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.reserve_memory_mib < 0:
            raise ValueError("reserve_memory_mib cannot be negative")
        if self.seed < 0:
            raise ValueError("seed cannot be negative")
        if self.vocab_size > MAX_VOCAB_SIZE:
            raise ValueError(f"vocab_size cannot exceed {MAX_VOCAB_SIZE}")
        if self.hidden_size % self.num_heads:
            raise ValueError("hidden_size must be divisible by num_heads")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must be in [0, 1)")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)
