"""CLI for a small, CPU-only educational training run."""

import argparse
import json
import signal
import threading
from pathlib import Path

from .training import train_tiny_model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="Local UTF-8 text file")
    parser.add_argument("--output", default="neural_lab_runs/first", help="Run output directory")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--context", type=int, default=32)
    parser.add_argument("--hidden", type=int, default=16)
    parser.add_argument("--layers", type=int, default=1)
    parser.add_argument("--heads", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--budget-mib", type=int, default=256)
    parser.add_argument("--reserve-mib", type=int, default=1536)
    parser.add_argument("--resume", help="Checkpoint produced by this Neural Lab")
    args = parser.parse_args()
    cancelled = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: cancelled.set())
    result = train_tiny_model(
        args.dataset, Path(args.output), context_length=args.context, hidden_size=args.hidden,
        num_layers=args.layers, num_heads=args.heads, batch_size=args.batch_size,
        max_steps=args.steps, memory_budget_mib=args.budget_mib,
        reserve_memory_mib=args.reserve_mib, resume_from=args.resume, cancel_event=cancelled,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
