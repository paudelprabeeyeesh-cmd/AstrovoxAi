#!/usr/bin/env python3
"""Train 100M parameter model."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_base import run_training

if __name__ == "__main__":
    run_training(config_path="models/llm/configs/config_100m.yaml")
