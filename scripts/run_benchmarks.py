#!/usr/bin/env python3
"""CLI runner for AstrovoxAi benchmark lab.

Usage examples:
    python scripts/run_benchmarks.py --suite standard --model my_model --device cuda
    python scripts/run_benchmarks.py --benchmarks mmlu gsm8k --max-samples 500
    python scripts/run_benchmarks.py --quick
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.benchmarks.harness import BenchmarkHarness, BenchmarkSuiteConfig
from models.llm.benchmarks.reporter import BenchmarkReporter
from models.llm.benchmarks.regression import RegressionDetector
from models.llm.benchmarks.suites import BENCHMARK_SUITES, get_suite, list_suites
from models.llm.evaluation.benchmarks import BENCHMARK_REGISTRY


def _load_model_and_tokenizer(model_name: str, device: str = "cpu"):
    try:
        import torch
        from models.llm.model.model import LLM
        from models.llm.tokenizer.train_tokenizer import load_tokenizer

        config_path = os.path.join(ROOT, "models", "llm", "configs", "config_100m.yaml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config not found: {config_path}")

        import yaml
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        model = LLM(config).to(device)
        model.eval()

        tokenizer_path = os.path.join(ROOT, "models", "llm", "tokenizer.json")
        if not os.path.exists(tokenizer_path):
            raise FileNotFoundError(f"Tokenizer not found: {tokenizer_path}")
        tokenizer = load_tokenizer(tokenizer_path)
        return model, tokenizer
    except Exception as exc:
        print(f"Warning: could not load real model ({exc}), using mock model.")
        return _make_mock_model(), _make_mock_tokenizer()


def _make_mock_model():
    class MockModel:
        def __init__(self):
            self.device = "cpu"

        def eval(self):
            return self

        def train(self):
            return self

        def __call__(self, input_ids, labels=None, **kwargs):
            import torch
            vocab_size = input_ids.shape[-1] if input_ids.shape[-1] > 0 else 100
            logits = torch.zeros(input_ids.shape[0], input_ids.shape[1], vocab_size)
            loss = torch.tensor(0.5) if labels is not None else None
            return {"logits": logits, "loss": loss}

        def generate(self, input_ids, max_new_tokens=64, pad_token_id=0, **kwargs):
            import torch
            batch_size = input_ids.shape[0]
            new_tokens = torch.randint(0, 100, (batch_size, max_new_tokens))
            return torch.cat([input_ids, new_tokens], dim=-1)

    return MockModel()


def _make_mock_tokenizer():
    class MockTokenizer:
        pad_token_id = 0
        eos_token_id = 1

        def __call__(self, text, **kwargs):
            import torch
            input_ids = torch.randint(0, 100, (1, 8))
            return type("obj", (object,), {"input_ids": input_ids})()

        def decode(self, token_ids, skip_special_tokens=False):
            return "mock answer"

    return MockTokenizer()


def run_benchmarks(args: argparse.Namespace) -> int:
    if args.list_suites:
        print("Available benchmark suites:")
        for name in list_suites():
            suite = get_suite(name)
            print(f"  {name}: {suite.description}")
        return 0

    if args.list_benchmarks:
        print("Available benchmarks:")
        for name in sorted(BENCHMARK_REGISTRY.keys()):
            print(f"  {name}")
        return 0

    benchmarks = args.benchmarks
    if args.suite:
        suite = get_suite(args.suite)
        benchmarks = suite.benchmarks
        if not benchmarks:
            print(f"Suite '{args.suite}' has no benchmarks defined.")
            return 1

    if not benchmarks:
        print("No benchmarks specified. Use --suite or --benchmarks.")
        return 1

    device = args.device
    model, tokenizer = _load_model_and_tokenizer(args.model, device=device)
    harness = BenchmarkHarness(model, tokenizer, model_name=args.model, device=device)

    output_path = args.output
    config = BenchmarkSuiteConfig(
        benchmarks=benchmarks,
        device=device,
        output_path=output_path,
        max_samples=args.max_samples,
    )

    print(f"Running benchmarks: {', '.join(benchmarks)}")
    report = harness.evaluate(config)
    print(report.summary())

    reporter = BenchmarkReporter(results_dir=os.path.dirname(output_path) or ".")

    md_path = output_path.replace(".json", "_report.md") if output_path.endswith(".json") else output_path + "_report.md"
    md_content = reporter.generate_markdown_report(report.to_dict(), title=f"Benchmark Report: {args.model}")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"Markdown report saved to: {md_path}")

    html_path = output_path.replace(".json", "_report.html") if output_path.endswith(".json") else output_path + "_report.html"
    reporter.generate_html_report(report.to_dict(), title=f"Benchmark Report: {args.model}", output_path=html_path)
    print(f"HTML report saved to: {html_path}")

    if args.baseline:
        detector = RegressionDetector(results_dir=os.path.dirname(output_path) or ".")
        try:
            summary = detector.compare(args.baseline, output_path)
            alert = detector.alert_if_regression(summary)
            if alert:
                print(alert)
            else:
                print("No regressions detected.")
            regression_path = detector.save_summary(summary)
            print(f"Regression summary saved to: {regression_path}")
        except Exception as exc:
            print(f"Regression comparison failed: {exc}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AstrovoxAi Benchmark Lab Runner")
    parser.add_argument("--model", default="astrovox-model", help="Model name")
    parser.add_argument("--device", default="cpu", help="Device: cpu or cuda")
    parser.add_argument("--benchmarks", nargs="*", default=[], help="Benchmark names to run")
    parser.add_argument("--suite", default=None, help="Benchmark suite name")
    parser.add_argument("--max-samples", type=int, default=1000, help="Max samples per benchmark")
    parser.add_argument("--output", default="benchmark_results/latest.json", help="Output path")
    parser.add_argument("--baseline", default=None, help="Baseline report path for regression detection")
    parser.add_argument("--list-suites", action="store_true", help="List available suites")
    parser.add_argument("--list-benchmarks", action="store_true", help="List available benchmarks")
    parser.add_argument("--quick", action="store_true", help="Run quick evaluation")

    args = parser.parse_args(argv)

    if args.quick:
        args.benchmarks = [
            "mmlu",
            "hellaswag",
            "arc",
            "gsm8k",
            "humaneval",
            "mbpp",
            "truthfulqa",
            "winogrande",
            "piqa",
        ]
        args.output = args.output or "benchmark_results/quick_eval.json"

    return run_benchmarks(args)


if __name__ == "__main__":
    sys.exit(main())
