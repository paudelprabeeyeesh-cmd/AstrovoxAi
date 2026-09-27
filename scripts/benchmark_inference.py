#!/usr/bin/env python3
"""
Benchmark inference throughput and latency.

Usage:
    python scripts/benchmark_inference.py --config configs/config_100m.yaml --prompts 20
"""

import argparse
import os
import sys
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.inference.engine import InferenceEngine, SamplingParams
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import load_config, get_device


PROMPTS = [
    "Once upon a time in a distant galaxy,",
    "The future of artificial intelligence is",
    "In the beginning of the universe,",
    "Python is a powerful programming language because",
    "The quick brown fox jumps over",
    "To be or not to be,",
    "Climate change is one of the most pressing issues",
    "The invention of the printing press revolutionized",
    "Space exploration has always fascinated humanity because",
    "A healthy diet consists of",
]


def main():
    parser = argparse.ArgumentParser(description="Benchmark inference throughput")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--checkpoint", default="model.pt")
    parser.add_argument("--prompts", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/inference_benchmark.json")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    device = args.device or get_device()
    config = load_config(args.config)

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    if os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device, weights_only=True))
    model.eval()

    tokenizer = load_tokenizer(config.get("tokenizer_path", "models/llm/tokenizer.json"))
    engine = InferenceEngine(model, tokenizer, device=torch.device(device), dtype=torch.float32)

    prompts = (PROMPTS * ((args.prompts // len(PROMPTS)) + 1))[: args.prompts]
    params = SamplingParams(max_new_tokens=args.max_tokens, temperature=1.0)

    latencies = []
    tokens_per_sec = []
    for i, prompt in enumerate(prompts):
        start = time.perf_counter()
        output = engine.generate(prompt, params)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        tps = output.num_tokens / elapsed if elapsed > 0 else 0
        tokens_per_sec.append(tps)
        if i % 10 == 0:
            print(f"Prompt {i + 1}/{len(prompts)}: {elapsed:.3f}s, {tps:.1f} tok/s")

    result = {
        "model_params": sum(p.numel() for p in model.parameters()),
        "device": device,
        "num_prompts": len(prompts),
        "max_tokens": args.max_tokens,
        "latencies_seconds": latencies,
        "tokens_per_second": tokens_per_sec,
        "avg_latency_seconds": sum(latencies) / len(latencies),
        "avg_tokens_per_second": sum(tokens_per_sec) / len(tokens_per_sec),
        "p50_latency_seconds": sorted(latencies)[len(latencies) // 2],
        "p95_latency_seconds": sorted(latencies)[int(len(latencies) * 0.95)],
    }

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nAverage latency: {result['avg_latency_seconds']:.3f}s")
    print(f"Average throughput: {result['avg_tokens_per_second']:.1f} tok/s")
    print(f"P50 latency: {result['p50_latency_seconds']:.3f}s")
    print(f"P95 latency: {result['p95_latency_seconds']:.3f}s")
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
