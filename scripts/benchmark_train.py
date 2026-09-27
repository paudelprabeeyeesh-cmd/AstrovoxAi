#!/usr/bin/env python3
"""
Benchmark training throughput and memory.

Usage:
    python scripts/benchmark_train.py --config configs/config_100m.yaml --iterations 3
"""

import argparse
import os
import sys
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.model.model_scaling import estimate_config
from models.llm.utils.helpers import load_config, get_device


def main():
    parser = argparse.ArgumentParser(description="Benchmark training throughput")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/training_benchmark.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    device = args.device or get_device()
    config = load_config(args.config)

    report = estimate_config(args.config)
    num_params = report["num_params"]
    print(f"Model size: {num_params:,} parameters")

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    model.train()

    dummy_input = torch.randint(0, config["vocab_size"], (config["batch_size"], config.get("max_position_embeddings", 1024)), device=device)
    dummy_labels = dummy_input.clone()

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

    times = []
    for i in range(args.iterations):
        torch.cuda.synchronize() if device == "cuda" else None
        start = time.perf_counter()
        optimizer.zero_grad()
        out = model(dummy_input, labels=dummy_labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
        loss = out["loss"]
        loss.backward()
        optimizer.step()
        torch.cuda.synchronize() if device == "cuda" else None
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        print(f"Iteration {i + 1}/{args.iterations}: {elapsed:.3f}s (loss: {loss.item():.4f})")

    result = {
        "model_params": num_params,
        "device": device,
        "iterations": args.iterations,
        "times_seconds": times,
        "avg_time_seconds": sum(times) / len(times),
        "min_time_seconds": min(times),
        "max_time_seconds": max(times),
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nAverage: {result['avg_time_seconds']:.3f}s")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
