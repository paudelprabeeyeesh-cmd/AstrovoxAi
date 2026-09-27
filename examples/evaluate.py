#!/usr/bin/env python3
"""
Run model evaluation benchmarks.

Usage:
    python examples/evaluate.py --checkpoint model.pt --benchmarks mmlu hellaswag gsm8k
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.inference.engine import InferenceEngine
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.evaluation.benchmarks import EvaluationHarness
from models.llm.utils.helpers import load_config, get_device, set_cpu_threads


def main():
    parser = argparse.ArgumentParser(description="Evaluate a model on benchmarks")
    parser.add_argument("--checkpoint", default="model.pt", help="Path to model checkpoint")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--benchmarks", nargs="+", default=["mmlu", "hellaswag", "gsm8k", "humaneval", "mbpp", "piqa", "boolq", "winogrande"])
    parser.add_argument("--max-samples", type=int, default=500)
    parser.add_argument("--output", default="eval_report.json")
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    device = args.device or get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    config = load_config(args.config)
    dtype = torch.float32
    if device == "cuda" and config.get("mixed_precision") == "fp16":
        dtype = torch.float16

    model = LLM(config, device=torch.device(device), dtype=dtype)
    if os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device, weights_only=True))
    model.eval()

    tokenizer = load_tokenizer(config.get("tokenizer_path", "models/llm/tokenizer.json"))
    engine = InferenceEngine(model, tokenizer, device=torch.device(device), dtype=dtype)

    harness = EvaluationHarness(engine, tokenizer, model_name="astrovox-model", device=device)
    report = harness.evaluate(args.benchmarks, max_samples=args.max_samples, output_path=args.output)

    print(harness._summary(report["results"]))
    print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
