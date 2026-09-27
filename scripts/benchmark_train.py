#!/usr/bin/env python3
"""Benchmark training throughput, memory usage, and checkpoint size."""

import argparse
import gc
import os
import sys
import time
import uuid
import warnings
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from model.model_scaling import estimate_config
from models.llm.utils.helpers import load_config, get_device
from models.llm.benchmarking import BenchmarkSuite, BenchmarkRun, SystemMonitor


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark training throughput")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--device", default=None)
    parser.add_argument("--output", default="benchmark_results/training_benchmark")
    parser.add_argument("--checkpoint-path", default=None)
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup iterations")
    parser.add_argument("--val-iterations", type=int, default=5, help="Validation iterations")
    args = parser.parse_args()

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    device = args.device or get_device()
    config = load_config(args.config)
    scaling_report = estimate_config(args.config)
    num_params = scaling_report["num_params"]

    print(f"Model size: {num_params:,} parameters")
    print(f"Device: {device}")

    suite = BenchmarkSuite(output_dir=args.output)
    monitor = SystemMonitor(interval=0.5)

    model = None
    checkpoint_size_mb = None

    try:
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

        times = []
        losses = []
        total_tokens = config["batch_size"] * config.get("max_position_embeddings", 1024)

        total_iterations = args.warmup + args.iterations

        for i in range(total_iterations):
            if device == "cuda":
                torch.cuda.synchronize()
            start = time.perf_counter()

            optimizer.zero_grad()
            out = model(
                dummy_input,
                labels=dummy_labels,
                use_gradient_checkpointing=config.get("gradient_checkpointing", False),
            )
            loss = out["loss"]
            loss.backward()
            optimizer.step()

            if device == "cuda":
                torch.cuda.synchronize()

            elapsed = time.perf_counter() - start
            if i >= args.warmup:
                times.append(elapsed)
                losses.append(loss.item())
                print(
                    f"Iteration {i - args.warmup + 1}/{args.iterations}: "
                    f"{elapsed:.3f}s (loss: {loss.item():.4f})"
                )

        # Validation loss and perplexity
        model.eval()
        val_losses = []
        with torch.no_grad():
            for _ in range(args.val_iterations):
                val_out = model(dummy_input, labels=dummy_labels)
                val_losses.append(val_out["loss"].item())
        model.train()

        avg_val_loss = sum(val_losses) / len(val_losses) if val_losses else 0.0
        perplexity = math.exp(avg_val_loss) if avg_val_loss < 20 else float("inf")

        # Tokens per second
        avg_time = sum(times) / len(times) if times else 0.0
        tokens_per_sec = (total_tokens / avg_time) if avg_time > 0 else 0.0

        # Checkpoint size
        if args.checkpoint_path:
            ckpt_dir = os.path.dirname(args.checkpoint_path)
            if ckpt_dir:
                os.makedirs(ckpt_dir, exist_ok=True)
            torch.save(model.state_dict(), args.checkpoint_path)
            checkpoint_size_mb = os.path.getsize(args.checkpoint_path) / (1024 * 1024)
            print(f"Checkpoint saved to {args.checkpoint_path} ({checkpoint_size_mb:.2f} MB)")

        metrics = {
            "model_params": num_params,
            "device": device,
            "iterations": args.iterations,
            "warmup_iterations": args.warmup,
            "times_seconds": times,
            "avg_time_seconds": round(avg_time, 4),
            "min_time_seconds": round(min(times), 4) if times else 0.0,
            "max_time_seconds": round(max(times), 4) if times else 0.0,
            "losses": losses,
            "avg_train_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
            "val_losses": val_losses,
            "avg_val_loss": round(avg_val_loss, 4),
            "perplexity": round(perplexity, 4),
            "tokens_per_second": round(tokens_per_sec, 2),
            "total_tokens_per_step": total_tokens,
            "checkpoint_size_mb": checkpoint_size_mb,
        }

        run = BenchmarkRun(
            run_id=str(uuid.uuid4())[:8],
            name="training_benchmark",
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            config=config,
            metrics=metrics,
            system_samples=monitor.samples,
            notes="Benchmark training throughput with dummy data",
        )

        suite.add_run(run)
        leak_report = suite.detect_memory_leaks(run)
        md_path, json_path = suite.save_reports(run, leak_report=leak_report)

        print(f"\nAverage step time: {metrics['avg_time_seconds']:.3f}s")
        print(f"Throughput: {metrics['tokens_per_second']:.1f} tokens/sec")
        print(f"Avg train loss: {metrics['avg_train_loss']:.4f}")
        print(f"Avg val loss: {metrics['avg_val_loss']:.4f}")
        print(f"Perplexity: {metrics['perplexity']:.4f}")
        print(f"Results saved to {args.output}")
        print(f"Markdown: {md_path}")
        print(f"JSON: {json_path}")

        return 0

    except Exception as e:
        print(f"Error during training benchmark: {e}", file=sys.stderr)
        warnings.warn(f"Training benchmark failed: {e}")
        return 1

    finally:
        monitor.stop()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


if __name__ == "__main__":
    sys.exit(main())
