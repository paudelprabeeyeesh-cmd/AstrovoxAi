#!/usr/bin/env python3
"""
Train a tiny model from scratch.

Usage:
    python examples/train_tiny.py --config configs/config_100m.yaml
"""

import argparse
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.llm.trainer.train import train
from models.llm.model.model_scaling import print_scaling_report


def main():
    parser = argparse.ArgumentParser(description="Train a tiny LLM")
    parser.add_argument("--config", default="models/llm/configs/config_100m.yaml", help="Path to YAML config")
    parser.add_argument("--report", action="store_true", help="Print scaling report before training")
    args = parser.parse_args()

    if args.report:
        print_scaling_report(args.config)

    print(f"Starting training with config: {args.config}")
    train(config_path=args.config)


if __name__ == "__main__":
    main()
