#!/usr/bin/env python3
"""Benchmark inference latency, tokens/sec, and batch size scaling."""

import argparse
import gc
import os
import sys
import time
import uuid
from typing import List, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.inference.engine import InferenceEngine, SamplingParams
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import load_config, get_device
from models.llm.benchmarking import BenchmarkSuite, BenchmarkRun, SystemMonitor


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


def benchmark_single_batch(
    engine: InferenceEngine,
    prompts: List[str],
    params: SamplingParams,
    monitor: SystemMonitor,
) -> dict:
    """Benchmark a single batch of prompts and return metrics."""
    latencies = []
    tokens_per_sec = []

    for i, prompt in enumerate(prompts):
        start = time.perf_counter()
        output = engine.generate(prompt, params)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        tps = output.num_tokens / elapsed if elapsed > 0 else 0.0
        tokens_per_sec.append(tps)
        if i % 10 == 0:
            print(f"Prompt {i + 1}/{len(prompts)}: {elapsed:.3f}s, {tps:.1f} tok/s")

    sorted_latencies = sorted(latencies)
    n = len(latencies)
    return {
        "num_prompts": len(prompts),
        "max_new_tokens": params.max_new_tokens,
        "latencies_seconds": latencies,
        "tokens_per_second": tokens_per_sec,
        "avg_latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
        "avg_tokens_per_second": round(sum(tokens_per_sec) / len(tokens_per_sec), 4) if tokens_per_sec else 0.0,
        "p50_latency_seconds": round(sorted_latencies[n // 2], 4) if n else 0.0,
        "p95_latency_seconds": round(sorted_latencies[int(n * 0.95)], 4) if n else 0.0,
        "p99_latency_seconds": round(sorted_latencies[int(n * 0.99)], 4) if n else 0.0,
        "min_latency_seconds": round(min(latencies), 4) if latencies else 0.0,
        "max_latency_seconds": round(max(latencies), 4) if latencies else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark inference throughput")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--checkpoint", default="model.pt")
    parser.add_argument("--prompts", type=int, default=10)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--batch-sizes", type=str, default="1,4,8", help="Comma-separated batch sizes to test")
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/inference_benchmark")
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    device = args.device or get_device()
    config = load_config(args.config)

    print(f"Loading model...")
    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    if os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device, weights_only=True))
    model.eval()

    tokenizer = load_tokenizer(config.get("tokenizer_path", "models/llm/tokenizer.json"))
    engine = InferenceEngine(model, tokenizer, device=torch.device(device), dtype=torch.float32)

    prompts = (PROMPTS * ((args.prompts // len(PROMPTS)) + 1))[: args.prompts]
    batch_sizes = [int(bs.strip()) for bs in args.batch_sizes.split(",") if bs.strip()]

    suite = BenchmarkSuite(output_dir=args.output)

    try:
        for bs in batch_sizes:
            print(f"\n{'=' * 60}")
            print(f"Benchmarking batch_size={bs}")
            print(f"{'=' * 60}")

            monitor = SystemMonitor(interval=0.5)
            monitor.start()

            batch_prompts = (prompts * ((bs // len(prompts)) + 1))[:bs] if bs > 1 else prompts[:1]
            params = SamplingParams(max_new_tokens=args.max_tokens, temperature=1.0)

            metrics = benchmark_single_batch(engine, batch_prompts, params, monitor)
            monitor.stop()

            run = BenchmarkRun(
                run_id=str(uuid.uuid4())[:8],
                name=f"inference_benchmark_bs{bs}",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                config=config,
                metrics=metrics,
                system_samples=monitor.samples,
                notes=f"Inference benchmark with batch_size={bs}",
            )

            suite.add_run(run)
            leak_report = suite.detect_memory_leaks(run)
            suite.save_reports(run, leak_report=leak_report)

            print(
                f"Batch size {bs}: avg_latency={metrics['avg_latency_seconds']:.3f}s, "
                f"avg_tokens_per_sec={metrics['avg_tokens_per_second']:.1f}, "
                f"p95_latency={metrics['p95_latency_seconds']:.3f}s"
            )

        comparison = suite.compare_runs()
        suite.save_comparison_report(comparison)

        print(f"\nResults saved to {args.output}")
        return 0

    except Exception as e:
        print(f"Error during inference benchmark: {e}", file=sys.stderr)
        return 1

    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    sys.exit(main())
