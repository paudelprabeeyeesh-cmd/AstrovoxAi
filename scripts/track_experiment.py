#!/usr/bin/env python3
"""CLI for experiment tracking."""

from __future__ import annotations

import argparse
import json
import os
import sys

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.tracking.experiment import Experiment
from models.llm.tracking.metrics import MetricStore
from models.llm.tracking.reports import ReportGenerator


MANIFEST_FILE = "experiments/manifest.json"


def load_manifest(storage_dir: str) -> dict[str, Any]:
    path = os.path.join(storage_dir, MANIFEST_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(storage_dir: str, manifest: dict[str, Any]) -> None:
    os.makedirs(storage_dir, exist_ok=True)
    path = os.path.join(storage_dir, MANIFEST_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def cmd_start(args: argparse.Namespace) -> None:
    exp = Experiment(name=args.name, storage_dir=args.storage_dir)
    run = exp.start_run()
    manifest = load_manifest(args.storage_dir)
    manifest.setdefault("experiments", {})[exp.experiment_id] = {"name": args.name}
    manifest.setdefault("runs", {})[run.run_id] = {"experiment_id": exp.experiment_id, "experiment_name": args.name}
    save_manifest(args.storage_dir, manifest)
    print(json.dumps({"experiment_id": exp.experiment_id, "run_id": run.run_id, "name": args.name}))


def cmd_stop(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.storage_dir)
    run_meta = manifest.get("runs", {}).get(args.run_id)
    if not run_meta:
        print(f"Run {args.run_id} not found in manifest")
        sys.exit(1)
    exp = Experiment(name=run_meta["experiment_name"], storage_dir=args.storage_dir)
    exp.experiment_id = run_meta["experiment_id"]
    exp.stop_run(args.run_id)
    print(f"Stopped run {args.run_id}")


def cmd_log(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.storage_dir)
    run_meta = manifest.get("runs", {}).get(args.run_id)
    if not run_meta:
        print(f"Run {args.run_id} not found in manifest")
        sys.exit(1)
    exp = Experiment(name=run_meta["experiment_name"], storage_dir=args.storage_dir)
    exp.experiment_id = run_meta["experiment_id"]
    exp.log_metric(args.run_id, args.key, args.value)
    print(f"Logged {args.key}={args.value}")


def cmd_param(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.storage_dir)
    run_meta = manifest.get("runs", {}).get(args.run_id)
    if not run_meta:
        print(f"Run {args.run_id} not found in manifest")
        sys.exit(1)
    params = json.loads(args.params)
    exp = Experiment(name=run_meta["experiment_name"], storage_dir=args.storage_dir)
    exp.experiment_id = run_meta["experiment_id"]
    exp.log_parameters(args.run_id, params)
    print(f"Logged parameters for run {args.run_id}")


def cmd_report(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.storage_dir)
    exp_meta = manifest.get("experiments", {}).get(args.experiment_name)
    if not exp_meta:
        # Try matching by name if ID lookup fails
        for exp_id, meta in manifest.get("experiments", {}).items():
            if meta.get("name") == args.experiment_name:
                exp_meta = meta
                break
    if not exp_meta:
        print(f"Experiment {args.experiment_name} not found")
        sys.exit(1)
    exp = Experiment(name=exp_meta["name"], storage_dir=args.storage_dir)
    exp.experiment_id = args.experiment_name
    # Reconstruct runs from manifest
    for run_id, run_meta in manifest.get("runs", {}).items():
        if run_meta.get("experiment_id") == args.experiment_name:
            run = exp.start_run(run_name=run_meta.get("experiment_name", ""))
            # Override run_id since start_run creates a new one
            exp.runs[run.run_id] = exp.runs.pop(run.run_id)
            exp.runs[run.run_id].run_id = run_id
    generator = ReportGenerator(exp)
    generator.generate_html(args.output)
    print(f"Report generated: {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AstrovoxAi Experiment Tracker")
    subparsers = parser.add_subparsers(dest="command")

    start_parser = subparsers.add_parser("start", help="Start a new experiment")
    start_parser.add_argument("name", help="Experiment name")
    start_parser.add_argument("--storage-dir", default="experiments", help="Storage directory")

    stop_parser = subparsers.add_parser("stop", help="Stop a run")
    stop_parser.add_argument("run_id", help="Run ID to stop")
    stop_parser.add_argument("--storage-dir", default="experiments", help="Storage directory")

    log_parser = subparsers.add_parser("log", help="Log a metric")
    log_parser.add_argument("run_id", help="Run ID")
    log_parser.add_argument("key", help="Metric key")
    log_parser.add_argument("value", type=float, help="Metric value")
    log_parser.add_argument("--storage-dir", default="experiments", help="Storage directory")

    param_parser = subparsers.add_parser("param", help="Log parameters")
    param_parser.add_argument("run_id", help="Run ID")
    param_parser.add_argument("params", help="JSON string of parameters")
    param_parser.add_argument("--storage-dir", default="experiments", help="Storage directory")

    report_parser = subparsers.add_parser("report", help="Generate report")
    report_parser.add_argument("experiment_name", help="Experiment name or ID")
    report_parser.add_argument("--output", default="report.html", help="Output path")
    report_parser.add_argument("--storage-dir", default="experiments", help="Storage directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "param":
        cmd_param(args)
    elif args.command == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
