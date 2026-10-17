"""Conservative training-memory estimates and admission checks."""

from dataclasses import dataclass

import psutil

from .config import TinyTransformerConfig

MIB = 1024 * 1024


@dataclass(frozen=True)
class MemoryEstimate:
    parameter_count: int
    parameter_and_optimizer_bytes: int
    activation_bytes: int
    estimated_total_bytes: int
    available_bytes: int | None
    budget_bytes: int


def estimate_training_memory(config: TinyTransformerConfig) -> MemoryEstimate:
    """Estimate float32 weights, gradients, Adam moments, logits, and saved activations."""
    c = config
    # Embeddings, attention projections, two-layer MLP, and layer norms; deliberately over-count bias/norm terms.
    per_layer = 4 * c.hidden_size**2 + 2 * c.hidden_size * (c.hidden_size * c.mlp_ratio) + 8 * c.hidden_size
    params = c.vocab_size * c.hidden_size + c.context_length * c.hidden_size + c.num_layers * per_layer + c.hidden_size * c.vocab_size + 2 * c.hidden_size
    # fp32 weights + grads + two Adam state tensors. This excludes Python/PyTorch runtime overhead.
    state_bytes = params * 16
    token_acts = c.batch_size * c.context_length * c.hidden_size * (4 * c.num_layers + 8)
    attention_acts = c.batch_size * c.num_heads * c.context_length**2 * c.num_layers
    logits = c.batch_size * c.context_length * c.vocab_size
    activation_bytes = (token_acts + attention_acts + logits) * 4 * 2
    total = state_bytes + activation_bytes
    try:
        available = psutil.virtual_memory().available
    except (AttributeError, OSError, RuntimeError):
        available = None
    return MemoryEstimate(params, state_bytes, activation_bytes, total, available, c.memory_budget_mib * MIB)


def enforce_memory_budget(config: TinyTransformerConfig, estimate: MemoryEstimate | None = None) -> MemoryEstimate:
    estimate = estimate or estimate_training_memory(config)
    if estimate.estimated_total_bytes > estimate.budget_bytes:
        raise MemoryError(
            f"estimated training use {estimate.estimated_total_bytes / MIB:.1f} MiB exceeds "
            f"configured budget {estimate.budget_bytes / MIB:.1f} MiB"
        )
    if estimate.available_bytes is not None:
        required = estimate.estimated_total_bytes + config.reserve_memory_mib * MIB
        if required > estimate.available_bytes:
            raise MemoryError(
                f"estimated training use plus {config.reserve_memory_mib} MiB reserve exceeds "
                "currently available system memory"
            )
    return estimate
