"""Omega-10: Benchmark research covering major LLM benchmarks and leaderboards."""

import json
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import torch

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    PERPLEXITY = "perplexity"
    ACCURACY = "accuracy"
    F1 = "f1"
    EXACT_MATCH = "exact_match"
    BLEU = "bleu"
    ROUGE = "rouge"
    MMLU = "mmlu"
    HUMAN_EVAL = "human_eval"
    GSM8K = "gsm8k"
    MT_BENCH = "mt_bench"
    HELM = "helm"


@dataclass
class BenchmarkResult:
    benchmark: str
    score: float
    stderr: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkConfig:
    benchmarks: List[BenchmarkType] = field(default_factory=lambda: list(BenchmarkType))
    num_fewshot: int = 0
    batch_size: int = 8
    device: str = "cuda" if torch.cuda.is_available() else "cpu"


class PerplexityBenchmark:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, model, tokenizer, dataset) -> BenchmarkResult:
        total_loss = 0.0
        total_tokens = 0
        for batch in dataset:
            with torch.no_grad():
                outputs = model(**batch)
                loss = outputs.loss
                total_loss += loss.item() * batch["input_ids"].numel()
                total_tokens += batch["input_ids"].numel()
        avg_loss = total_loss / total_tokens
        return BenchmarkResult(benchmark="perplexity", score=math.exp(avg_loss))


class AccuracyBenchmark:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, model, tokenizer, dataset) -> BenchmarkResult:
        correct = 0
        total = 0
        for batch in dataset:
            with torch.no_grad():
                outputs = model.generate(**batch)
                predictions = outputs.sequences
                labels = batch["labels"]
                correct += (predictions == labels).sum().item()
                total += labels.numel()
        return BenchmarkResult(benchmark="accuracy", score=correct / total if total > 0 else 0.0)


class MMLUBenchmark:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, model, tokenizer, dataset) -> BenchmarkResult:
        correct = 0
        total = 0
        for item in dataset:
            prompt = item["question"]
            choices = item["choices"]
            correct_answer = item["answer"]
            scores = []
            for choice in choices:
                inputs = tokenizer(prompt + " " + choice, return_tensors="pt")
                with torch.no_grad():
                    outputs = model(**inputs)
                    score = -outputs.loss.item()
                scores.append(score)
            predicted = torch.argmax(torch.tensor(scores)).item()
            if predicted == correct_answer:
                correct += 1
            total += 1
        return BenchmarkResult(benchmark="mmlu", score=correct / total if total > 0 else 0.0)


class HumanEvalBenchmark:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, model, tokenizer, dataset) -> BenchmarkResult:
        correct = 0
        total = 0
        for item in dataset:
            prompt = item["prompt"]
            inputs = tokenizer(prompt, return_tensors="pt")
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=512)
            generated = tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)
            if item["test"] in generated:
                correct += 1
            total += 1
        return BenchmarkResult(benchmark="human_eval", score=correct / total if total > 0 else 0.0)


class GSM8KBenchmark:
    def __init__(self, config: BenchmarkConfig):
        self.config = config

    def evaluate(self, model, tokenizer, dataset) -> BenchmarkResult:
        correct = 0
        total = 0
        for item in dataset:
            prompt = item["question"]
            inputs = tokenizer(prompt, return_tensors="pt")
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=256)
            generated = tokenizer.decode(outputs.sequences[0], skip_special_tokens=True)
            if item["answer"] in generated:
                correct += 1
            total += 1
        return BenchmarkResult(benchmark="gsm8k", score=correct / total if total > 0 else 0.0)


class BenchmarkSuite:
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.benchmarks: Dict[str, Any] = {
            "perplexity": PerplexityBenchmark(self.config),
            "accuracy": AccuracyBenchmark(self.config),
            "mmlu": MMLUBenchmark(self.config),
            "human_eval": HumanEvalBenchmark(self.config),
            "gsm8k": GSM8KBenchmark(self.config),
        }
        self._results: List[BenchmarkResult] = []

    def run(self, model, tokenizer, dataset) -> List[BenchmarkResult]:
        results = []
        for name, benchmark in self.benchmarks.items():
            if name in self.config.benchmarks:
                try:
                    result = benchmark.evaluate(model, tokenizer, dataset)
                    results.append(result)
                    self._results.append(result)
                except Exception as e:
                    logger.error("Benchmark %s failed: %s", name, e)
        return results

    def generate_leaderboard(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        scores = {r.benchmark: r.score for r in results}
        overall = sum(scores.values()) / len(scores) if scores else 0.0
        return {"overall": overall, "breakdown": scores, "num_benchmarks": len(scores)}


class BenchmarkResearch:
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig()
        self.suite = BenchmarkSuite(config)

    def run_full_evaluation(self, model, tokenizer, dataset) -> Dict[str, Any]:
        results = self.suite.run(model, tokenizer, dataset)
        return self.suite.generate_leaderboard(results)
