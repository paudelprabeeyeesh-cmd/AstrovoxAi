#!/usr/bin/env python3
"""
Benchmark memory usage for model loading and inference.

Usage:
    python scripts/benchmark_memory.py --config configs/config_4b.yaml
"""

import argparse
import gc
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.model.model_scaling import estimate_config
from models.llm.utils.helpers import load_config, get_device


def get_gpu_memory():
    if torch.cuda.is_available():
        return torch.cuda.memory_allocated() / (1024 ** 2), torch.cuda.max_memory_allocated() / (1024 ** 2)
    return 0.0, 0.0


def main():
    parser = argparse.ArgumentParser(description="Benchmark memory usage")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/memory_benchmark.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    device = args.device or get_device()
    config = load_config(args.config)

    gc.collect()
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    report = estimate_config(args.config)
    num_params = report["num_params"]
    print(f"Model: {num_params:,} parameters")
    print(f"Estimated weights: {report['memory']['weights_gb']:.2f} GB")

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    current_mem, peak_mem = get_gpu_memory()
    print(f"After load: {current_mem:.1f} MB (peak: {peak_mem:.1f} MB)")

    model.eval()
    dummy_input = torch.randint(0, config["vocab_size"], (1, 128), device=device)
    with torch.no_grad():
        for _ in range(5):
            _ = model(dummy_input)
    current_mem, peak_mem = get_gpu_memory()
    print(f"After inference: {current_mem:.1f} MB (peak: {peak_mem:.1f} MB)")

    result = {
        "model_params": num_params,
        "device": device,
        "estimated_weights_gb": report["memory"]["weights_gb"],
        "estimated_train_gb": report["memory"]["total_base_gb"],
        "gpu_allocated_mb": current_mem,
        "gpu_peak_mb": peak_mem,
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
