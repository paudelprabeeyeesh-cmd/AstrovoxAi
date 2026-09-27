#!/usr/bin/env python3
"""
Instruction tuning (fine-tuning) example.

Usage:
    python examples/finetune.py --config configs/config_finetune.yaml --model model.pt
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.llm.trainer.finetune import finetune


def main():
    parser = argparse.ArgumentParser(description="Fine-tune a model on instruction data")
    parser.add_argument("--config", required=True, help="Fine-tuning config YAML")
    parser.add_argument("--model", required=True, help="Path to pretrained checkpoint")
    parser.add_argument("--output-dir", default=None, help="Output directory for fine-tuned model")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        raise FileNotFoundError(f"Checkpoint not found: {args.model}")

    print(f"Fine-tuning with config: {args.config}")
    print(f"Base model: {args.model}")
    finetune(config_path=args.config, model_path=args.model, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
