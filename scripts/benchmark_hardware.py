#!/usr/bin/env python3
"""CLI for running hardware benchmarks and generating reports."""

import argparse
import gc
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch

from models.llm.benchmarking import BenchmarkSuite
from models.llm.benchmarks.hardware import (
    AmdBenchmark,
    AppleSiliconBenchmark,
    BenchmarkResult,
    CostPerTokenCalculator,
    IntelCpuBenchmark,
    MemoryBandwidthBenchmark,
    NvidiaBenchmark,
)
from models.llm.benchmarks.profiles import detect_hardware, get_apple_silicon_profile, get_cpu_profile, get_gpu_profile, list_apple_silicon_profiles, list_cpu_profiles, list_gpu_profiles
from models.llm.model.model import LLM
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import get_device, load_config


def build_tiny_config() -> dict:
    return {
        "vocab_size": 1000,
        "hidden_size": 32,
        "num_hidden_layers": 2,
        "num_attention_heads": 2,
        "intermediate_size": 64,
        "max_position_embeddings": 64,
        "rms_norm_eps": 1e-5,
        "rope_theta": 10000.0,
        "activation": "swiglu",
        "attention_bias": False,
        "mlp_bias": False,
        "dropout": 0.0,
        "tie_weights": True,
        "batch_size": 2,
    }


def run_benchmarks(args: argparse.Namespace) -> int:
    output_dir = args.output
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    suite = BenchmarkSuite(output_dir=output_dir or "benchmark_results/hardware")
    profile = get_profile(args)
    if profile is None:
        print("No suitable hardware profile found or specified.", file=sys.stderr)
        return 1

    device = args.device or get_device()
    config = build_tiny_config() if not args.config else load_config(args.config)

    if args.list_profiles:
        print("GPU profiles:", list_gpu_profiles())
        print("CPU profiles:", list_cpu_profiles())
        print("Apple Silicon profiles:", list_apple_silicon_profiles())
        return 0

    if args.compare:
        return run_comparison(args, suite, device, config)

    model = None
    tokenizer = None
    try:
        model = LLM(config, device=torch.device(device), dtype=torch.float32)
        model.eval()
        tokenizer = load_tokenizer(args.tokenizer or "models/llm/tokenizer.json")
    except Exception as e:
        print(f"Failed to load model/tokenizer: {e}", file=sys.stderr)

    prompts = [
        "Once upon a time in a distant galaxy,",
        "The future of artificial intelligence is",
        "In the beginning of the universe,",
        "Python is a powerful programming language because",
        "The quick brown fox jumps over",
    ][: args.prompts]

    benchmark = get_benchmark(profile, device)
    results: list[BenchmarkResult] = []

    if args.inference:
        result = benchmark.inference_benchmark(model, tokenizer, prompts, max_new_tokens=args.max_tokens, device=device)
        results.append(result)

    if args.training:
        result = benchmark.training_benchmark(model, config, steps=args.train_steps, device=device)
        results.append(result)

    if args.memory_bandwidth:
        bw_benchmark = MemoryBandwidthBenchmark(profile)
        result = bw_benchmark.run(size_mb=args.bandwidth_size, device=device)
        results.append(result)

    if args.power:
        power_benchmark = NvidiaBenchmark(profile) if profile.device_type == "gpu" and profile.vendor == "nvidia" else None
        if power_benchmark is None:
            print("Power measurement currently supported only for NVIDIA GPUs.", file=sys.stderr)
        else:
            result = power_benchmark.power_usage_benchmark(device=device)
            results.append(result)

    if args.cost_per_token:
        tps = args.tokens_per_second or results[0].metrics.get("avg_tokens_per_second", 0.0) if results else 0.0
        calculator = CostPerTokenCalculator(profile)
        cost_metrics = calculator.calculate(tps)
        result = BenchmarkResult(
            name=f"cost_per_token_{profile.name}",
            metrics=cost_metrics,
            profile=profile,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        results.append(result)

    for result in results:
        suite.add_run(
            type(
                "",
                (object,),
                {
                    "run_id": str(uuid.uuid4())[:8],
                    "name": result.name,
                    "timestamp": result.timestamp,
                    "config": config,
                    "metrics": result.metrics,
                    "system_samples": [],
                    "notes": args.notes or "",
                },
            )()
        )
        md_path, json_path = suite.save_reports(
            type(
                "",
                (object,),
                {
                    "run_id": str(uuid.uuid4())[:8],
                    "name": result.name,
                    "timestamp": result.timestamp,
                    "config": config,
                    "metrics": result.metrics,
                    "system_samples": [],
                    "notes": args.notes or "",
                },
            )()
        )
        print(f"Saved {result.name}: {md_path}")

    return 0


def run_comparison(args: argparse.Namespace, suite: BenchmarkSuite, device: str, config: dict) -> int:
    if not args.compare:
        return 0
    names = [n.strip() for n in args.compare.split(",") if n.strip()]
    if not names:
        print("No profiles specified for comparison.", file=sys.stderr)
        return 1

    model = None
    tokenizer = None
    try:
        model = LLM(config, device=torch.device(device), dtype=torch.float32)
        model.eval()
        tokenizer = load_tokenizer(args.tokenizer or "models/llm/tokenizer.json")
    except Exception as e:
        print(f"Failed to load model/tokenizer: {e}", file=sys.stderr)
        model = None
        tokenizer = None

    prompts = [
        "Once upon a time in a distant galaxy,",
        "The future of artificial intelligence is",
        "In the beginning of the universe,",
        "Python is a powerful programming language because",
        "The quick brown fox jumps over",
    ]

    run_ids: list[str] = []
    for name in names:
        profile = get_profile_by_name(name)
        if profile is None:
            print(f"Profile not found: {name}", file=sys.stderr)
            continue
        benchmark = get_benchmark(profile, device)
        result = benchmark.inference_benchmark(model, tokenizer, prompts, max_new_tokens=args.max_tokens, device=device)
        run = type(
            "",
            (object,),
            {
                "run_id": str(uuid.uuid4())[:8],
                "name": result.name,
                "timestamp": result.timestamp,
                "config": config,
                "metrics": result.metrics,
                "system_samples": [],
                "notes": args.notes or "",
                "to_dict": lambda self: {k: v for k, v in self.__dict__.items() if k != "to_dict"},
            },
        )()
        suite.add_run(run)
        run_ids.append(run.run_id)
        print(f"Ran {result.name}")

    if len(run_ids) >= 2:
        comparison = suite.compare_runs(run_ids)
        suite.save_comparison_report(comparison)
        print(f"Comparison report saved to {suite.output_dir}")

    return 0


def get_profile(args: argparse.Namespace):
    if args.profile:
        return get_profile_by_name(args.profile)
    return detect_hardware()


def get_profile_by_name(name: str):
    for lookup in (get_gpu_profile, get_cpu_profile, get_apple_silicon_profile):
        try:
            return lookup(name)
        except KeyError:
            continue
    return None


def get_benchmark(profile, device: str):
    if profile.device_type == "gpu" and profile.vendor == "nvidia":
        return NvidiaBenchmark(profile)
    if profile.device_type == "gpu" and profile.vendor == "amd":
        return AmdBenchmark(profile)
    if profile.device_type == "cpu":
        return IntelCpuBenchmark(profile)
    if profile.device_type == "apple_silicon":
        return AppleSiliconBenchmark(profile)
    return IntelCpuBenchmark(profile)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hardware benchmark CLI")
    parser.add_argument("--config", default=None, help="Path to model config YAML")
    parser.add_argument("--tokenizer", default="models/llm/tokenizer.json", help="Path to tokenizer")
    parser.add_argument("--device", default=None, help="Device override")
    parser.add_argument("--output", default="benchmark_results/hardware", help="Output directory")
    parser.add_argument("--profile", default=None, help="Hardware profile name")
    parser.add_argument("--list-profiles", action="store_true", help="List available hardware profiles")
    parser.add_argument("--inference", action="store_true", help="Run inference benchmark")
    parser.add_argument("--training", action="store_true", help="Run training benchmark")
    parser.add_argument("--memory-bandwidth", action="store_true", help="Run memory bandwidth benchmark")
    parser.add_argument("--power", action="store_true", help="Run power usage benchmark")
    parser.add_argument("--cost-per-token", action="store_true", help="Calculate cost per token")
    parser.add_argument("--prompts", type=int, default=5, help="Number of prompts for inference benchmark")
    parser.add_argument("--max-tokens", type=int, default=32, help="Max new tokens for inference benchmark")
    parser.add_argument("--train-steps", type=int, default=3, help="Number of training steps")
    parser.add_argument("--bandwidth-size", type=int, default=256, help="Memory bandwidth test size in MB")
    parser.add_argument("--tokens-per-second", type=float, default=None, help="Tokens per second for cost calculation")
    parser.add_argument("--compare", default=None, help="Comma-separated profile names for comparison")
    parser.add_argument("--notes", default="", help="Notes for the benchmark run")
    args = parser.parse_args()

    if not any([args.inference, args.training, args.memory_bandwidth, args.power, args.cost_per_token, args.compare, args.list_profiles]):
        args.inference = True

    try:
        return run_benchmarks(args)
    except Exception as e:
        print(f"Error during hardware benchmark: {e}", file=sys.stderr)
        return 1
    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    sys.exit(main())
