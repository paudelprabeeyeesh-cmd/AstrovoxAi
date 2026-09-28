from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from models.llm.evaluation.benchmarks import (
    BENCHMARK_REGISTRY,
    BaseBenchmark,
    BenchmarkResult,
)


@dataclass
class BenchmarkSuite:
    name: str
    benchmarks: List[str]
    description: str = ""
    prompt_template: Optional[str] = None
    scoring: str = "accuracy"

    def get_benchmark_instances(self, max_samples: int = 1000) -> Dict[str, BaseBenchmark]:
        instances: Dict[str, BaseBenchmark] = {}
        for name in self.benchmarks:
            if name not in BENCHMARK_REGISTRY:
                raise KeyError(
                    f"Benchmark '{name}' is not registered. Available: {sorted(BENCHMARK_REGISTRY.keys())}"
                )
            instances[name] = BENCHMARK_REGISTRY[name](max_samples=max_samples)
        return instances

    def score(self, results: Dict[str, BenchmarkResult]) -> float:
        if not results:
            return 0.0
        if self.scoring == "accuracy":
            valid = [r.score for r in results.values()]
            return sum(valid) / len(valid)
        if self.scoring == "mean_stderr":
            return sum(r.stderr for r in results.values()) / len(results)
        raise ValueError(f"Unsupported scoring method: {self.scoring}")


BENCHMARK_SUITES: Dict[str, BenchmarkSuite] = {
    "mmlu": BenchmarkSuite(
        name="mmlu",
        benchmarks=["mmlu"],
        description="Massive Multitask Language Understanding",
        scoring="accuracy",
    ),
    "hellaswag": BenchmarkSuite(
        name="hellaswag",
        benchmarks=["hellaswag"],
        description="HellaSwag commonsense reasoning",
        scoring="accuracy",
    ),
    "arc": BenchmarkSuite(
        name="arc",
        benchmarks=["arc"],
        description="AI2 Reasoning Challenge",
        scoring="accuracy",
    ),
    "gsm8k": BenchmarkSuite(
        name="gsm8k",
        benchmarks=["gsm8k"],
        description="Grade school math reasoning",
        scoring="accuracy",
    ),
    "humaneval": BenchmarkSuite(
        name="humaneval",
        benchmarks=["humaneval"],
        description="HumanEval code generation",
        scoring="accuracy",
    ),
    "mbpp": BenchmarkSuite(
        name="mbpp",
        benchmarks=["mbpp"],
        description="Mostly Basic Python Problems",
        scoring="accuracy",
    ),
    "truthfulqa": BenchmarkSuite(
        name="truthfulqa",
        benchmarks=["truthfulqa"],
        description="TruthfulQA factual accuracy",
        scoring="accuracy",
    ),
    "winogrande": BenchmarkSuite(
        name="winogrande",
        benchmarks=["winogrande"],
        description="Winogrande commonsense reasoning",
        scoring="accuracy",
    ),
    "piqa": BenchmarkSuite(
        name="piqa",
        benchmarks=["piqa"],
        description="Physical Interaction QA",
        scoring="accuracy",
    ),
    "bbh": BenchmarkSuite(
        name="bbh",
        benchmarks=[],
        description="BIG-Bench Hard",
        scoring="accuracy",
    ),
    "mt_bench": BenchmarkSuite(
        name="mt_bench",
        benchmarks=[],
        description="MT-Bench conversational evaluation",
        scoring="accuracy",
    ),
    "standard": BenchmarkSuite(
        name="standard",
        benchmarks=[
            "mmlu",
            "hellaswag",
            "arc",
            "gsm8k",
            "humaneval",
            "mbpp",
            "truthfulqa",
            "winogrande",
            "piqa",
        ],
        description="Standard multi-domain evaluation suite",
        scoring="accuracy",
    ),
}


PROMPT_TEMPLATES: Dict[str, str] = {
    "mmlu": (
        "Question: {question}\n"
        "{choices}\n"
        "Please answer with the letter of the correct option.\n"
        "Answer:"
    ),
    "arc": (
        "Question: {question}\n"
        "{choices}\n"
        "Answer:"
    ),
    "gsm8k": (
        "Solve the following math problem step by step.\n"
        "Question: {question}\n"
        "Answer:"
    ),
    "humaneval": "{prompt}",
    "mbpp": "{prompt}\n",
    "truthfulqa": (
        "Question: {question}\n"
        "Please answer truthfully and concisely.\n"
        "Answer:"
    ),
    "winogrande": "{sentence}",
    "piqa": (
        "Goal: {goal}\n"
        "Which of the following is the correct way to accomplish this goal?\n"
        "1) {sol1}\n"
        "2) {sol2}\n"
        "Answer with 1 or 2:"
    ),
}


def get_suite(name: str) -> BenchmarkSuite:
    if name not in BENCHMARK_SUITES:
        raise KeyError(f"Unknown benchmark suite: {name}. Available: {sorted(BENCHMARK_SUITES.keys())}")
    return BENCHMARK_SUITES[name]


def list_suites() -> List[str]:
    return sorted(BENCHMARK_SUITES.keys())


def build_prompt(benchmark_name: str, example: Dict[str, Any]) -> str:
    template = PROMPT_TEMPLATES.get(benchmark_name, "{question}")
    try:
        return template.format(**example)
    except Exception:
        return str(example)
