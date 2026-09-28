#!/usr/bin/env python3
"""CLI harness for Phase E hyperparameter search."""

import argparse
import logging
import sys
from pathlib import Path

from models.llm.hyperparameter_search import HyperparameterSearch


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LLM hyperparameter search (Phase E)")
    parser.add_argument(
        "--config", default="models/llm/configs/config_phase1.yaml", help="Base YAML config path"
    )
    parser.add_argument(
        "--search-type", choices=["optuna", "random", "auto"], default="auto", help="Search backend"
    )
    parser.add_argument("--n-trials", type=int, default=20, help="Number of trials to run")
    parser.add_argument(
        "--output-dir",
        default="hyperparameter_search",
        help="Output directory for logs and configs",
    )
    parser.add_argument("--study-name", default="llm_search", help="Study name")
    parser.add_argument(
        "--direction",
        choices=["minimize", "maximize"],
        default="minimize",
        help="Optimization direction",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--max-trial-steps", type=int, default=50, help="Max training steps per trial"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate markdown report after search"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    if args.n_trials < 1:
        print("--n-trials must be >= 1")
        return 1
    if args.max_trial_steps < 1:
        print("--max-trial-steps must be >= 1")
        return 1

    try:
        search = HyperparameterSearch(
            base_config_path=args.config,
            n_trials=args.n_trials,
            output_dir=args.output_dir,
            study_name=args.study_name,
            direction=args.direction,
            seed=args.seed,
            max_trial_steps=args.max_trial_steps,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1

    try:
        result = search.run(search_type=args.search_type)
    except Exception as exc:
        logging.getLogger(__name__).exception("Search failed")
        print(f"Search failed: {exc}")
        return 1

    print("\nSearch completed successfully.")
    print(f"  Best score : {result['best_value']:.6f}")
    print(f"  Best config: {result['best_config_path']}")
    print(f"  Experiment log: {result['log_path']}")

    if args.report:
        report = search.generate_report()
        report_path = Path(result["report_path"])
        report_path.write_text(report, encoding="utf-8")
        print(f"  Report     : {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
