import math
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def count_parameters(hidden_size, vocab_size, num_hidden_layers, num_attention_heads, intermediate_size, max_position_embeddings):
    head_dim = hidden_size // num_attention_heads
    params = 0
    params += vocab_size * hidden_size
    params += max_position_embeddings * hidden_size
    per_block = 0
    per_block += 2 * hidden_size
    per_block += 4 * hidden_size * hidden_size
    per_block += 2 * hidden_size
    per_block += hidden_size * intermediate_size + intermediate_size * hidden_size
    params += num_hidden_layers * per_block
    params += 2 * hidden_size
    params += hidden_size * vocab_size
    return params


def memory_estimation(num_params, dtype_bytes=2, training=True):
    weights_mem = num_params * dtype_bytes
    grad_mem = weights_mem if training else 0
    optimizer_mem = weights_mem * 2 if training else 0
    base_mem = weights_mem + grad_mem + optimizer_mem
    return {
        "weights_gb": weights_mem / (1024 ** 3),
        "gradients_gb": grad_mem / (1024 ** 3),
        "optimizer_gb": optimizer_mem / (1024 ** 3),
        "total_base_gb": base_mem / (1024 ** 3),
    }


def chinchilla_optimal_tokens(num_params):
    return 20 * num_params


def estimate_training_time(num_params, tokens_per_second, optimal_tokens=None):
    if optimal_tokens is None:
        optimal_tokens = chinchilla_optimal_tokens(num_params)
    steps = optimal_tokens / 2048
    seconds = steps / tokens_per_second
    days = seconds / 86400
    return {"steps": int(steps), "seconds": seconds, "days": days}


def load_config(config_path="models/llm/configs/config_100m.yaml"):
    if yaml is None:
        raise ImportError("PyYAML is required to load configs. Install it with: pip install pyyaml")
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def estimate_config(config_path="models/llm/configs/config_100m.yaml", dtype_bytes=2, training=True):
    config = load_config(config_path)
    num_params = count_parameters(
        hidden_size=config["hidden_size"],
        vocab_size=config["vocab_size"],
        num_hidden_layers=config["num_hidden_layers"],
        num_attention_heads=config["num_attention_heads"],
        intermediate_size=config["intermediate_size"],
        max_position_embeddings=config["max_position_embeddings"],
    )
    mem = memory_estimation(num_params, dtype_bytes=dtype_bytes, training=training)
    optimal_tokens = chinchilla_optimal_tokens(num_params)
    return {
        "config_path": config_path,
        "num_params": num_params,
        "memory": mem,
        "optimal_tokens": optimal_tokens,
        "config": config,
    }


def hardware_requirements(config_path="models/llm/configs/config_100m.yaml"):
    report = estimate_config(config_path)
    num_params = report["num_params"]
    p_label = f"{num_params / 1e9:.1f}B" if num_params >= 1e9 else f"{num_params / 1e6:.0f}M"

    if num_params <= 200e6:
        cpu_inference = "8GB+ RAM"
        cpu_training = "16GB+ RAM"
        gpu_inference = "4GB+ VRAM (CPU fallback viable)"
        gpu_training = "8GB+ VRAM with gradient checkpointing"
    elif num_params <= 1e9:
        cpu_inference = "16GB+ RAM"
        cpu_training = "32GB+ RAM (slow)"
        gpu_inference = "16GB+ VRAM (RTX 4080/4090, A10)"
        gpu_training = "24GB+ VRAM (RTX 4090, A10) with gradient checkpointing"
    elif num_params <= 3e9:
        cpu_inference = "32GB+ RAM"
        cpu_training = "64GB+ RAM (impractical)"
        gpu_inference = "24GB+ VRAM (A10, RTX 4090)"
        gpu_training = "40GB+ VRAM (A100) or 2x RTX 4090 with DeepSpeed/FSDP"
    elif num_params <= 8e9:
        cpu_inference = "64GB+ RAM (slow)"
        cpu_training = "128GB+ RAM (impractical)"
        gpu_inference = "40GB+ VRAM (A100) or 2x A10"
        gpu_training = "2x A100 40GB/80GB or 4x RTX 4090 with DeepSpeed/FSDP + gradient checkpointing"
    else:
        cpu_inference = "128GB+ RAM"
        cpu_training = "256GB+ RAM (cluster required)"
        gpu_inference = "Multi-GPU node required"
        gpu_training = "Multi-GPU cluster with tensor parallelism"

    return {
        "model_size": p_label,
        "cpu_inference_ram": cpu_inference,
        "cpu_training_ram": cpu_training,
        "gpu_inference_vram": gpu_inference,
        "gpu_training_vram": gpu_training,
        "notes": (
            "Memory estimates assume fp16/bfloat16 training. "
            "INT4/INT8 quantization can roughly halve inference VRAM. "
            "Gradient checkpointing trades compute for memory. "
            "Chinchilla-optimal training data: ~20 tokens per parameter."
        ),
    }


def print_scaling_report(config_path="models/llm/configs/config_100m.yaml"):
    report = estimate_config(config_path)
    hw = hardware_requirements(config_path)
    num_params = report["num_params"]
    p_label = hw["model_size"]

    print("=" * 60)
    print(f"Scaling Report: {Path(config_path).name}")
    print("=" * 60)
    print(f"Parameters:       {num_params:,} ({p_label})")
    print(f"Optimal tokens:   {report['optimal_tokens']:,}")
    print()
    print("Memory Requirements (fp16/bfloat16):")
    print(f"  Weights:        {report['memory']['weights_gb']:.2f} GB")
    print(f"  Gradients:      {report['memory']['gradients_gb']:.2f} GB")
    print(f"  Optimizer:      {report['memory']['optimizer_gb']:.2f} GB")
    print(f"  Total (train):  {report['memory']['total_base_gb']:.2f} GB")
    print()
    print("Hardware Guidance:")
    print(f"  CPU inference:  {hw['cpu_inference_ram']}")
    print(f"  CPU training:   {hw['cpu_training_ram']}")
    print(f"  GPU inference:  {hw['gpu_inference_vram']}")
    print(f"  GPU training:   {hw['gpu_training_vram']}")
    print()
    print("Notes:")
    print(f"  {hw['notes']}")
    print("=" * 60)
