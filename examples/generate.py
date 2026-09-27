#!/usr/bin/env python3
"""
Basic text generation example.

Usage:
    python examples/generate.py --prompt "Once upon a time" --checkpoint model.pt
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch
from models.llm.model.model import LLM
from models.llm.inference.engine import InferenceEngine, SamplingParams
from models.llm.tokenizer.train_tokenizer import load_tokenizer
from models.llm.utils.helpers import load_config, get_device, set_cpu_threads


def main():
    parser = argparse.ArgumentParser(description="Generate text from a prompt")
    parser.add_argument("--prompt", required=True, help="Input prompt")
    parser.add_argument("--checkpoint", default="model.pt", help="Path to model checkpoint")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml")
    parser.add_argument("--max-tokens", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--top-p", type=float, default=None)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    device = args.device or get_device()
    if device == "cpu":
        set_cpu_threads(min(4, os.cpu_count() or 2))

    config = load_config(args.config)
    dtype = torch.float32
    if device == "cuda":
        if config.get("mixed_precision") == "fp16":
            dtype = torch.float16
        elif config.get("mixed_precision") == "bf16":
            dtype = torch.bfloat16
    elif device == "cpu":
        if config.get("mixed_precision") == "bf16" and hasattr(torch, "bfloat16"):
            dtype = torch.bfloat16

    model = LLM(config, device=torch.device(device), dtype=dtype)
    if os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device, weights_only=True))
    model.eval()

    tokenizer = load_tokenizer(config.get("tokenizer_path", "models/llm/tokenizer.json"))
    engine = InferenceEngine(model, tokenizer, device=torch.device(device), dtype=dtype)

    params = SamplingParams(
        max_new_tokens=args.max_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        repetition_penalty=args.repetition_penalty,
    )
    output = engine.generate(args.prompt, params)
    print(f"\nPrompt: {args.prompt}")
    print(f"Generated: {output.text}")
    print(f"\nTokens: {output.num_tokens} | Latency: {output.latency_ms:.1f}ms")


if __name__ == "__main__":
    main()
