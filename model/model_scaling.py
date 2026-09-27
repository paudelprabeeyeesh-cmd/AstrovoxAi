import math
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def count_parameters(hidden_size, vocab_size, num_hidden_layers, num_attention_heads, intermediate_size, max_position_embeddings):
    per_block = 0
    per_block += 2 * hidden_size
    per_block += 4 * (hidden_size * hidden_size + hidden_size)
    per_block += 2 * hidden_size
    per_block += hidden_size * intermediate_size + intermediate_size
    per_block += intermediate_size * hidden_size + hidden_size
    params = vocab_size * hidden_size + max_position_embeddings * hidden_size
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
        runnable = True
        gpu_inference_specific = "Any modern GPU (GTX 1650+, RTX 3050+, MX550)"
        gpu_training_specific = "RTX 3050 (6GB), RTX 3060 (12GB), or any GPU with 8GB+ VRAM"
        tpu_specific = "TPU not required; CPU or single GPU sufficient"
    elif num_params <= 2e9:
        cpu_inference = "16GB+ RAM"
        cpu_training = "32GB+ RAM (slow)"
        gpu_inference = "12-16GB VRAM (RTX 3060/4070, A10)"
        gpu_training = "24GB VRAM (RTX 3090/4090, A10) with gradient checkpointing"
        runnable = False
        gpu_inference_specific = "RTX 3060 12GB, RTX 4070 12GB, RTX 4090 24GB, or A10 24GB"
        gpu_training_specific = "RTX 3090 24GB, RTX 4090 24GB, A10 24GB, or A100 40GB"
        tpu_specific = "TPU v3-8 or v4-8 for faster training; single GPU preferred"
    elif num_params <= 5e9:
        cpu_inference = "32GB+ RAM"
        cpu_training = "64GB+ RAM (impractical)"
        gpu_inference = "24GB VRAM (A10, RTX 4090) or 2x RTX 3060 with tensor parallelism"
        gpu_training = "A100 40GB/80GB or 2x RTX 4090 (24GB each) with DeepSpeed/FSDP + gradient checkpointing"
        runnable = False
        gpu_inference_specific = "A10 24GB, RTX 4090 24GB, or 2x RTX 3090/4090 with tensor parallelism"
        gpu_training_specific = "A100 40GB/80GB (1x), A10 24GB (2x with DeepSpeed ZeRO Stage 2), RTX 4090 24GB (2x with FSDP)"
        tpu_specific = "TPU v3-8 (128GB HBM) or v4-8 for single-node training"
    elif num_params <= 10e9:
        cpu_inference = "64GB+ RAM (slow)"
        cpu_training = "128GB+ RAM (impractical)"
        gpu_inference = "40GB VRAM (A100) or 2x A10 with tensor parallelism"
        gpu_training = "2x A100 40GB/80GB or 4x RTX 4090 with DeepSpeed ZeRO Stage 3 + gradient checkpointing"
        runnable = False
        gpu_inference_specific = "A100 40GB/80GB (1x), A10 24GB (2x with tensor parallelism), A40 48GB"
        gpu_training_specific = "A100 40GB/80GB (2x with FSDP/DeepSpeed ZeRO Stage 3), A40 48GB (2x), RTX 4090 24GB (4x)"
        tpu_specific = "TPU v3-32 or v4-32 for production training; v4-8 minimum for experimentation"
    elif num_params <= 20e9:
        cpu_inference = "128GB+ RAM"
        cpu_training = "256GB+ RAM (cluster required)"
        gpu_inference = "80GB+ VRAM (A100 80GB) or 2x A100 40GB with tensor parallelism"
        gpu_training = "4x A100 80GB with FSDP/tensor parallelism + gradient checkpointing"
        runnable = False
        gpu_inference_specific = "A100 80GB (1x), A100 40GB (2x with tensor parallelism), A40 48GB (2x)"
        gpu_training_specific = "A100 80GB (4x with FSDP), A100 40GB (4x), or equivalent cluster"
        tpu_specific = "TPU v4-64 or v4-128 for production; v4-32 for development"
    else:
        cpu_inference = "256GB+ RAM"
        cpu_training = "512GB+ RAM (cluster required)"
        gpu_inference = "Multi-GPU node required"
        gpu_training = "Multi-GPU cluster with tensor parallelism + ZeRO stage 3"
        runnable = False
        gpu_inference_specific = "Multi-GPU node (8x A100 80GB) with tensor parallelism"
        gpu_training_specific = "8x+ A100 80GB cluster with FSDP + pipeline parallelism"
        tpu_specific = "TPU v4 pod or larger for production training"

    return {
        "model_size": p_label,
        "cpu_inference_ram": cpu_inference,
        "cpu_training_ram": cpu_training,
        "gpu_inference_vram": gpu_inference,
        "gpu_training_vram": gpu_training,
        "gpu_inference_specific": gpu_inference_specific,
        "gpu_training_specific": gpu_training_specific,
        "tpu_specific": tpu_specific,
        "runnable_locally": runnable,
        "notes": (
            "Memory estimates assume fp16/bfloat16 training. "
            "INT4/INT8 quantization can roughly halve inference VRAM. "
            "Gradient checkpointing trades compute for memory. "
            "Chinchilla-optimal training data: ~20 tokens per parameter."
        ),
    }


def training_recipe(config_path="models/llm/configs/config_100m.yaml"):
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
    elif num_params <= 5e9:
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
    elif num_params <= 10e9:
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


def print_scaling_report(config_path="models/llm/configs/config_100m.yaml"):
    report = estimate_config(config_path)
    hw = hardware_requirements(config_path)
    recipe = training_recipe(config_path)
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
    print(f"  GPU inference (specific):  {hw['gpu_inference_specific']}")
    print(f"  GPU training (specific):   {hw['gpu_training_specific']}")
    print(f"  TPU guidance:   {hw['tpu_specific']}")
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
    print("=" * 60)


if __name__ == "__main__":
    import sys
    cfg = sys.argv[1] if len(sys.argv) > 1 else "models/llm/configs/config_100m.yaml"
    print_scaling_report(cfg)
