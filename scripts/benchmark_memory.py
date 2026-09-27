#!/usr/bin/env python3
"""Profile memory usage during training and inference, detect leaks."""

import argparse
import gc
import math
import os
import sys
import time
import uuid
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from model.model_scaling import estimate_config
from models.llm.inference.engine import InferenceEngine, SamplingParams
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import load_config, get_device
from models.llm.benchmarking import BenchmarkSuite, BenchmarkRun, SystemMonitor


def profile_training_memory(
    config: dict,
    device: str,
    steps: int = 10,
    monitor_interval: float = 0.5,
) -> BenchmarkRun:
    """Run a short training loop and profile memory usage."""
    monitor = SystemMonitor(interval=monitor_interval)
    monitor.start()

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    model.train()

    dummy_input = torch.randint(
        0,
        config["vocab_size"],
        (config["batch_size"], config.get("max_position_embeddings", 1024)),
        device=device,
    )
    dummy_labels = dummy_input.clone()
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4)

    train_times = []
    for i in range(steps):
        if device == "cuda":
            torch.cuda.synchronize()
        start = time.perf_counter()

        optimizer.zero_grad()
        out = model(dummy_input, labels=dummy_labels, use_gradient_checkpointing=config.get("gradient_checkpointing", False))
        loss = out["loss"]
        loss.backward()
        optimizer.step()

        if device == "cuda":
            torch.cuda.synchronize()

        elapsed = time.perf_counter() - start
        train_times.append(elapsed)

    monitor.stop()

    # Peaks after training
    gpu_mem_after = None
    gpu_peak_after = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_mem_after = torch.cuda.memory_allocated() / (1024 * 1024)
            gpu_peak_after = torch.cuda.max_memory_allocated() / (1024 * 1024)
    except Exception:
        pass

    metrics = {
        "phase": "training",
        "steps": steps,
        "times_seconds": train_times,
        "avg_step_time_seconds": round(sum(train_times) / len(train_times), 4) if train_times else 0.0,
        "gpu_memory_after_mb": gpu_mem_after,
        "gpu_memory_peak_mb": gpu_peak_after,
    }

    run = BenchmarkRun(
        run_id=str(uuid.uuid4())[:8],
        name="memory_profile_training",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        config=config,
        metrics=metrics,
        system_samples=monitor.samples,
        notes="Memory profile during training",
    )
    return run


def profile_inference_memory(
    config: dict,
    device: str,
    num_prompts: int = 5,
    max_new_tokens: int = 32,
    monitor_interval: float = 0.5,
) -> BenchmarkRun:
    """Run inference and profile memory usage."""
    monitor = SystemMonitor(interval=monitor_interval)
    monitor.start()

    model = LLM(config, device=torch.device(device), dtype=torch.float32)
    model.eval()

    tokenizer = load_tokenizer(config.get("tokenizer_path", "models/llm/tokenizer.json"))
    engine = InferenceEngine(model, tokenizer, device=torch.device(device), dtype=torch.float32)

    prompts = [
        "Once upon a time in a distant galaxy,",
        "The future of artificial intelligence is",
        "In the beginning of the universe,",
        "Python is a powerful programming language because",
        "The quick brown fox jumps over",
    ][:num_prompts]

    params = SamplingParams(max_new_tokens=max_new_tokens, temperature=1.0)
    latencies = []
    for prompt in prompts:
        start = time.perf_counter()
        output = engine.generate(prompt, params)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

    monitor.stop()

    gpu_mem_after = None
    gpu_peak_after = None
    try:
        import torch
        if torch.cuda.is_available():
            gpu_mem_after = torch.cuda.memory_allocated() / (1024 * 1024)
            gpu_peak_after = torch.cuda.max_memory_allocated() / (1024 * 1024)
    except Exception:
        pass

    metrics = {
        "phase": "inference",
        "num_prompts": len(prompts),
        "max_new_tokens": max_new_tokens,
        "times_seconds": latencies,
        "avg_latency_seconds": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
        "gpu_memory_after_mb": gpu_mem_after,
        "gpu_memory_peak_mb": gpu_peak_after,
    }

    run = BenchmarkRun(
        run_id=str(uuid.uuid4())[:8],
        name="memory_profile_inference",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        config=config,
        metrics=metrics,
        system_samples=monitor.samples,
        notes="Memory profile during inference",
    )
    return run


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark memory usage")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/memory_benchmark")
    parser.add_argument("--train-steps", type=int, default=10)
    parser.add_argument("--inference-prompts", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    device = args.device or get_device()
    config = load_config(args.config)
    scaling_report = estimate_config(args.config)
    num_params = scaling_report["num_params"]

    print(f"Model: {num_params:,} parameters")
    print(f"Device: {device}")

    suite = BenchmarkSuite(output_dir=args.output)

    try:
        # Phase 1: Training memory profile
        print("\nPhase 1: Profiling memory during training...")
        train_run = profile_training_memory(config, device, steps=args.train_steps)
        suite.add_run(train_run)
        train_leak = suite.detect_memory_leaks(train_run)
        suite.save_reports(train_run, leak_report=train_leak)
        print(f"Training memory profile saved. Leak detected: {train_leak['leak_detected']}")

        # Phase 2: Inference memory profile
        print("\nPhase 2: Profiling memory during inference...")
        infer_run = profile_inference_memory(
            config, device, num_prompts=args.inference_prompts, max_new_tokens=args.max_new_tokens
        )
        suite.add_run(infer_run)
        infer_leak = suite.detect_memory_leaks(infer_run)
        suite.save_reports(infer_run, leak_report=infer_leak)
        print(f"Inference memory profile saved. Leak detected: {infer_leak['leak_detected']}")

        # Combined report
        print("\nPhase 3: Generating combined memory report...")
        comparison = suite.compare_runs()
        suite.save_comparison_report(comparison)

        # Memory summary
        train_summary = {
            "phase": "training",
            "run_id": train_run.run_id,
            "gpu_memory_after_mb": train_run.metrics.get("gpu_memory_after_mb"),
            "gpu_memory_peak_mb": train_run.metrics.get("gpu_memory_peak_mb"),
            "avg_step_time_seconds": train_run.metrics.get("avg_step_time_seconds"),
            "leak_detected": train_leak["leak_detected"],
        }
        infer_summary = {
            "phase": "inference",
            "run_id": infer_run.run_id,
            "gpu_memory_after_mb": infer_run.metrics.get("gpu_memory_after_mb"),
            "gpu_memory_peak_mb": infer_run.metrics.get("gpu_memory_peak_mb"),
            "avg_latency_seconds": infer_run.metrics.get("avg_latency_seconds"),
            "leak_detected": infer_leak["leak_detected"],
        }

        combined_report = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_params": num_params,
            "device": device,
            "phases": [train_summary, infer_summary],
            "comparison": comparison,
        }

        combined_path = suite.output_dir / "memory_profile_report.json"
        with open(combined_path, "w") as f:
            json.dump(combined_report, f, indent=2)

        md_lines = [
            "# Memory Profile Report",
            "",
            f"- **Timestamp:** {combined_report['timestamp']}",
            f"- **Model:** {num_params:,} parameters",
            f"- **Device:** {device}",
            "",
            "## Training Phase",
            f"- GPU Memory after: {train_summary.get('gpu_memory_after_mb', 'N/A')} MB",
            f"- GPU Memory peak: {train_summary.get('gpu_memory_peak_mb', 'N/A')} MB",
            f"- Avg step time: {train_summary.get('avg_step_time_seconds', 'N/A')}s",
            f"- Leak detected: {train_summary['leak_detected']}",
            "",
            "## Inference Phase",
            f"- GPU Memory after: {infer_summary.get('gpu_memory_after_mb', 'N/A')} MB",
            f"- GPU Memory peak: {infer_summary.get('gpu_memory_peak_mb', 'N/A')} MB",
            f"- Avg latency: {infer_summary.get('avg_latency_seconds', 'N/A')}s",
            f"- Leak detected: {infer_summary['leak_detected']}",
        ]
        combined_md_path = suite.output_dir / "memory_profile_report.md"
        with open(combined_md_path, "w") as f:
            f.write("\n".join(md_lines) + "\n")

        print(f"\nCombined memory profile saved to {args.output}")
        print(f"JSON: {combined_path}")
        print(f"Markdown: {combined_md_path}")
        return 0

    except Exception as e:
        print(f"Error during memory benchmark: {e}", file=sys.stderr)
        return 1

    finally:
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    sys.exit(main())
