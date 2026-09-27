import math
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None


def count_parameters(
    vocab_size: int,
    hidden_size: int,
    num_hidden_layers: int,
    num_attention_heads: int,
    intermediate_size: int,
    max_position_embeddings: int = 2048,
    attention_bias: bool = False,
    mlp_bias: bool = False,
    tie_weights: bool = True,
    activation: str = "swiglu",
) -> int:
    if hidden_size % num_attention_heads != 0:
        raise ValueError("hidden_size must be divisible by num_attention_heads")
    head_dim = hidden_size // num_attention_heads

    params = vocab_size * hidden_size
    if not tie_weights:
        params += hidden_size * vocab_size

    per_block = 0.0
    per_block += 2 * hidden_size  # RMSNorm weights (pre-attn + pre-mlp)

    q_params = head_dim * hidden_size * num_attention_heads
    k_params = head_dim * hidden_size * num_attention_heads
    v_params = head_dim * hidden_size * num_attention_heads
    o_params = hidden_size * hidden_size + (hidden_size if attention_bias else 0)
    per_block += q_params + k_params + v_params + o_params

    if activation == "swiglu":
        gate_params = hidden_size * intermediate_size + (intermediate_size if mlp_bias else 0)
        up_params = hidden_size * intermediate_size + (intermediate_size if mlp_bias else 0)
        down_params = intermediate_size * hidden_size + (hidden_size if mlp_bias else 0)
        per_block += gate_params + up_params + down_params
    else:
        up_params = hidden_size * intermediate_size + (intermediate_size if mlp_bias else 0)
        down_params = intermediate_size * hidden_size + (hidden_size if mlp_bias else 0)
        per_block += up_params + down_params

    params += num_hidden_layers * per_block
    params += 2 * hidden_size  # final RMSNorm
    if not tie_weights:
        params += hidden_size * vocab_size

    return int(params)


def memory_estimation(
    num_params: int,
    dtype_bytes: int = 2,
    training: bool = True,
    optimizer_overhead: float = 2.0,
    activation_checkpointing: bool = True,
    context_length: int = 2048,
    batch_size: int = 1,
    hidden_size: int = 4096,
    num_hidden_layers: int = 32,
) -> Dict[str, float]:
    weights_mem = num_params * dtype_bytes
    grad_mem = weights_mem if training else 0.0
    optimizer_mem = weights_mem * optimizer_overhead if training else 0.0

    activation_mem = 0.0
    if training:
        base_activation_per_layer = batch_size * context_length * hidden_size * 4 * dtype_bytes
        activation_mem = num_hidden_layers * base_activation_per_layer
        if activation_checkpointing:
            activation_mem = activation_mem / num_hidden_layers * 2

    total = weights_mem + grad_mem + optimizer_mem + activation_mem
    return {
        "weights_gb": weights_mem / (1024 ** 3),
        "gradients_gb": grad_mem / (1024 ** 3),
        "optimizer_gb": optimizer_mem / (1024 ** 3),
        "activations_gb": activation_mem / (1024 ** 3),
        "total_base_gb": total / (1024 ** 3),
    }


def chinchilla_optimal_tokens(num_params: int, tokens_per_param: float = 20.0) -> int:
    return int(num_params * tokens_per_param)


def estimate_training_time(
    num_params: int,
    tokens_per_second: float,
    optimal_tokens: Optional[int] = None,
    context_length: int = 2048,
) -> Dict[str, Union[int, float]]:
    if optimal_tokens is None:
        optimal_tokens = chinchilla_optimal_tokens(num_params)
    steps = optimal_tokens / context_length
    seconds = steps / tokens_per_second
    days = seconds / 86400.0
    return {
        "steps": int(steps),
        "seconds": seconds,
        "days": days,
        "optimal_tokens": optimal_tokens,
    }


def load_config(config_path: Union[str, Path] = "models/llm/configs/config_100m.yaml") -> Dict[str, Any]:
    if yaml is None:
        raise ImportError("PyYAML is required to load configs. Install it with: pip install pyyaml")
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def estimate_config(
    config_path: Union[str, Path] = "models/llm/configs/config_100m.yaml",
    dtype_bytes: int = 2,
    training: bool = True,
) -> Dict[str, Any]:
    config = load_config(config_path)
    num_params = count_parameters(
        vocab_size=int(config["vocab_size"]),
        hidden_size=int(config["hidden_size"]),
        num_hidden_layers=int(config["num_hidden_layers"]),
        num_attention_heads=int(config["num_attention_heads"]),
        intermediate_size=int(config["intermediate_size"]),
        max_position_embeddings=int(config.get("max_position_embeddings", 2048)),
        attention_bias=bool(config.get("attention_bias", False)),
        mlp_bias=bool(config.get("mlp_bias", False)),
        tie_weights=bool(config.get("tie_weights", True)),
        activation=str(config.get("activation", "swiglu")),
    )
    mem = memory_estimation(
        num_params,
        dtype_bytes=dtype_bytes,
        training=training,
        context_length=int(config.get("max_position_embeddings", 2048)),
        batch_size=int(config.get("batch_size", 1)),
    )
    optimal_tokens = chinchilla_optimal_tokens(num_params)
    return {
        "config_path": str(config_path),
        "num_params": num_params,
        "memory": mem,
        "optimal_tokens": optimal_tokens,
        "config": config,
    }


def hardware_requirements(
    config_path: Union[str, Path] = "models/llm/configs/config_100m.yaml",
    dtype_bytes: int = 2,
) -> Dict[str, Any]:
    report = estimate_config(config_path, dtype_bytes=dtype_bytes)
    num_params = report["num_params"]
    mem = report["memory"]
    p_label = f"{num_params / 1e9:.1f}B" if num_params >= 1e9 else f"{num_params / 1e6:.0f}M"

    if num_params <= 200e6:
        cpu_inference = "8GB+ RAM"
        cpu_training = "16GB+ RAM"
        gpu_inference = "4GB+ VRAM (CPU fallback viable)"
        gpu_training = "8GB+ VRAM with gradient checkpointing"
        runnable = True
    elif num_params <= 1e9:
        cpu_inference = "16GB+ RAM"
        cpu_training = "32GB+ RAM (slow)"
        gpu_inference = "16GB+ VRAM (RTX 4080/4090, A10)"
        gpu_training = "24GB+ VRAM (RTX 4090, A10) with gradient checkpointing"
        runnable = False
    elif num_params <= 3e9:
        cpu_inference = "32GB+ RAM"
        cpu_training = "64GB+ RAM (impractical)"
        gpu_inference = "24GB+ VRAM (A10, RTX 4090)"
        gpu_training = "40GB+ VRAM (A100) or 2x RTX 4090 with DeepSpeed/FSDP"
        runnable = False
    elif num_params <= 8e9:
        cpu_inference = "64GB+ RAM (slow)"
        cpu_training = "128GB+ RAM (impractical)"
        gpu_inference = "40GB+ VRAM (A100) or 2x A10"
        gpu_training = "2x A100 40GB/80GB or 4x RTX 4090 with DeepSpeed/FSDP + gradient checkpointing"
        runnable = False
    elif num_params <= 20e9:
        cpu_inference = "128GB+ RAM"
        cpu_training = "256GB+ RAM (cluster required)"
        gpu_inference = "80GB+ VRAM (A100 80GB) or 2x A100 40GB with tensor parallelism"
        gpu_training = "4x A100 80GB with FSDP/tensor parallelism + gradient checkpointing"
        runnable = False
    else:
        cpu_inference = "256GB+ RAM"
        cpu_training = "512GB+ RAM (cluster required)"
        gpu_inference = "Multi-GPU node required"
        gpu_training = "Multi-GPU cluster with tensor parallelism + ZeRO stage 3"
        runnable = False

    return {
        "model_size": p_label,
        "cpu_inference_ram": cpu_inference,
        "cpu_training_ram": cpu_training,
        "gpu_inference_vram": gpu_inference,
        "gpu_training_vram": gpu_training,
        "runnable_locally": runnable,
        "notes": (
            "Memory estimates assume fp16/bfloat16 training. "
            "INT4/INT8 quantization can roughly halve inference VRAM. "
            "Gradient checkpointing trades compute for memory. "
            "Chinchilla-optimal training data: ~20 tokens per parameter."
        ),
    }


def training_recipe(
    config_path: Union[str, Path] = "models/llm/configs/config_100m.yaml",
) -> Dict[str, Any]:
    report = estimate_config(config_path)
    hw = hardware_requirements(config_path)
    num_params = report["num_params"]
    optimal_tokens = report["optimal_tokens"]
    p_label = hw["model_size"]

    if num_params <= 200e6:
        return {
            "model_size": p_label,
            "runnable_locally": True,
            "optimizer": "AdamW (8-bit if bitsandbytes available, else standard)",
            "lr": "3e-4 with cosine annealing",
            "batch_size": "2-4 with gradient accumulation",
            "gradient_checkpointing": True,
            "mixed_precision": "fp16/bfloat16",
            "estimated_tokens_needed": optimal_tokens,
            "notes": (
                "This is the only config runnable on a typical consumer machine. "
                "Use gradient checkpointing to save memory. "
                "Train on a decent-sized text corpus (books, web text). "
                "Expected training time: hours to a day on a modern GPU."
            ),
        }
    elif num_params <= 3e9:
        return {
            "model_size": p_label,
            "runnable_locally": False,
            "optimizer": "AdamW 8-bit (bitsandbytes) or AdamW with CPU offloading",
            "lr": "3e-4 with cosine annealing, warmup 2-5% of steps",
            "batch_size": "4-8 with gradient accumulation (effective batch 512-2048)",
            "gradient_checkpointing": True,
            "mixed_precision": "fp16/bfloat16",
            "distributed": "DeepSpeed ZeRO Stage 2 or FSDP",
            "estimated_tokens_needed": optimal_tokens,
            "notes": (
                "Requires at least one 24-40GB GPU. "
                "Use FSDP or DeepSpeed ZeRO Stage 2 for multi-GPU. "
                "Consider QLoRA if fine-tuning on limited hardware. "
                "Expected training time: weeks on a single A100."
            ),
        }
    elif num_params <= 8e9:
        return {
            "model_size": p_label,
            "runnable_locally": False,
            "optimizer": "AdamW 8-bit (bitsandbytes) or CPU-offloaded AdamW",
            "lr": "2e-4 with cosine annealing, warmup 2-5% of steps",
            "batch_size": "8-16 with gradient accumulation (effective batch 1024-4096)",
            "gradient_checkpointing": True,
            "mixed_precision": "fp16/bfloat16",
            "distributed": "DeepSpeed ZeRO Stage 3 or FSDP with full sharding",
            "sequence_parallel": "Consider for sequences > 2048",
            "estimated_tokens_needed": optimal_tokens,
            "notes": (
                "Requires at least 2x A100 40GB or equivalent. "
                "Use ZeRO Stage 3 or FSDP with activation checkpointing. "
                "FlashAttention 2 is strongly recommended. "
                "Consider 4-bit QLoRA for fine-tuning. "
                "Expected training time: months on a small GPU cluster."
            ),
        }
    else:
        return {
            "model_size": p_label,
            "runnable_locally": False,
            "optimizer": "CPU-offloaded AdamW or fused AdamW",
            "lr": "1e-4 to 3e-4 with cosine annealing, warmup 1-3% of steps",
            "batch_size": "16-32+ with gradient accumulation (effective batch 4096-16384)",
            "gradient_checkpointing": True,
            "mixed_precision": "bfloat16 (fp16 may overflow at this scale)",
            "distributed": "FSDP with full sharding or DeepSpeed ZeRO Stage 3",
            "tensor_parallelism": "Required for inference on multi-GPU nodes",
            "sequence_parallel": "Required for sequences > 2048",
            "estimated_tokens_needed": optimal_tokens,
            "notes": (
                "Requires a multi-GPU cluster (4x+ A100 80GB). "
                "Use FSDP + activation checkpointing + FlashAttention 2/3. "
                "Consider pipeline parallelism if > 13B. "
                "Chinchilla-optimal data is critical at this scale. "
                "Expected training time: 6+ months on a modest cluster."
            ),
        }


def print_scaling_report(
    config_path: Union[str, Path] = "models/llm/configs/config_100m.yaml",
    dtype_bytes: int = 2,
):
    report = estimate_config(config_path, dtype_bytes=dtype_bytes)
    hw = hardware_requirements(config_path, dtype_bytes=dtype_bytes)
    recipe = training_recipe(config_path)
    num_params = report["num_params"]
    p_label = hw["model_size"]
    path = Path(config_path)

    print("=" * 70)
    print(f"Scaling Report: {path.name}")
    print("=" * 70)
    print(f"Parameters:       {num_params:,} ({p_label})")
    print(f"Optimal tokens:   {report['optimal_tokens']:,}")
    print()
    print("Memory Requirements (fp16/bfloat16):")
    print(f"  Weights:        {report['memory']['weights_gb']:.2f} GB")
    print(f"  Gradients:      {report['memory']['gradients_gb']:.2f} GB")
    print(f"  Optimizer:      {report['memory']['optimizer_gb']:.2f} GB")
    print(f"  Activations:    {report['memory']['activations_gb']:.2f} GB")
    print(f"  Total (train):  {report['memory']['total_base_gb']:.2f} GB")
    print()
    print("Hardware Guidance:")
    print(f"  CPU inference:  {hw['cpu_inference_ram']}")
    print(f"  CPU training:   {hw['cpu_training_ram']}")
    print(f"  GPU inference:  {hw['gpu_inference_vram']}")
    print(f"  GPU training:   {hw['gpu_training_vram']}")
    print(f"  Runnable locally: {'Yes (this machine)' if hw['runnable_locally'] else 'No (cluster required)'}")
    print()
    print("Training Recipe:")
    print(f"  Optimizer:      {recipe['optimizer']}")
    print(f"  Learning rate:  {recipe['lr']}")
    print(f"  Batch strategy: {recipe['batch_size']}")
    print(f"  Mixed precision: {recipe['mixed_precision']}")
    if "distributed" in recipe:
        print(f"  Distributed:    {recipe['distributed']}")
    print(f"  Data needed:    {recipe['estimated_tokens_needed']:,} tokens")
    print()
    print("Notes:")
    print(f"  {hw['notes']}")
    print(f"  {recipe['notes']}")
    print("=" * 70)


def compare_configs(
    config_paths: Optional[list] = None,
    base_dir: Union[str, Path] = "models/llm/configs",
) -> str:
    if config_paths is None:
        base = Path(base_dir)
        config_paths = sorted([str(p) for p in base.glob("config_*.yaml")])

    rows = []
    for path in config_paths:
        report = estimate_config(path)
        hw = hardware_requirements(path)
        cfg = report["config"]
        rows.append({
            "name": Path(path).stem,
            "params": report["num_params"],
            "size": hw["model_size"],
            "hidden": cfg.get("hidden_size"),
            "layers": cfg.get("num_hidden_layers"),
            "heads": cfg.get("num_attention_heads"),
            "ffn": cfg.get("intermediate_size"),
            "context": cfg.get("max_position_embeddings"),
            "weights_gb": report["memory"]["weights_gb"],
            "train_gb": report["memory"]["total_base_gb"],
        })

    header = f"{'Model':<10} {'Params':>10} {'Hidden':>7} {'Layers':>7} {'Heads':>7} {'FFN':>7} {'Ctx':>5} {'Weights GB':>11} {'Train GB':>10}"
    lines = [header, "-" * len(header)]
    for row in rows:
        lines.append(
            f"{row['name']:<10} {row['params']:>10,} {row['hidden']:>7} {row['layers']:>7} {row['heads']:>7} {row['ffn']:>7} {row['context']:>5} {row['weights_gb']:>11.2f} {row['train_gb']:>10.2f}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    cfg = sys.argv[1] if len(sys.argv) > 1 else "models/llm/configs/config_100m.yaml"
    if cfg == "--compare":
        base = sys.argv[2] if len(sys.argv) > 2 else "models/llm/configs"
        print(compare_configs(base_dir=base))
    else:
        print_scaling_report(cfg)
