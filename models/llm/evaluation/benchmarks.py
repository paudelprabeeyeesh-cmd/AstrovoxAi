import json
import math
import os
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch


@dataclass
class BenchmarkResult:
    name: str
    score: float
    stderr: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "stderr": self.stderr,
            "metadata": self.metadata,
        }


class BaseBenchmark(ABC):
    @abstractmethod
    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        raise NotImplementedError

    def _load_dataset(self, name: str, config: Optional[str] = None, split: str = "test"):
        try:
            from datasets import load_dataset
            if config:
                return load_dataset(name, config, split=split, streaming=True)
            return load_dataset(name, split=split, streaming=True)
        except Exception:
            return None

    def _generate_text(self, model, tokenizer, prompt: str, device: str, max_new_tokens: int = 256) -> str:
        model.eval()
        enc = tokenizer(prompt, truncation=True, max_length=1024, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0][enc.input_ids.shape[1]:], skip_special_tokens=True)

    def _choice_logprob(self, model, tokenizer, prompt: str, choices: List[str], device: str) -> int:
        scores = []
        for choice in choices:
            enc = tokenizer(prompt + " " + choice, truncation=True, max_length=1024, return_tensors="pt").to(device)
            labels = enc.input_ids.clone()
            with torch.no_grad():
                outputs = model(enc.input_ids, labels=labels)
                loss = outputs.get("loss") if isinstance(outputs, dict) else outputs[0]
            if loss is None:
                scores.append(float("-inf"))
            else:
                scores.append(-loss.item() * enc.input_ids.numel())
        return int(scores.index(max(scores)))

    def _exact_match(self, generated: str, reference: str) -> bool:
        gen = generated.strip().lower()
        ref = reference.strip().lower()
        return gen == ref or ref in gen


class MultipleChoiceBenchmark(BaseBenchmark):
    def __init__(self, dataset_name: str, config_name: Optional[str] = None, split: str = "test", max_samples: int = 1000):
        self.dataset_name = dataset_name
        self.config_name = config_name
        self.split = split
        self.max_samples = max_samples

    def prepare_dataset(self):
        return self._load_dataset(self.dataset_name, self.config_name, self.split)

    @abstractmethod
    def format_example(self, example: Dict[str, Any]) -> Tuple[str, List[str], int]:
        raise NotImplementedError

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        dataset = self.prepare_dataset()
        if dataset is None:
            return self._synthetic_run(model, tokenizer, device)
        for example in dataset:
            if total >= self.max_samples:
                break
            prompt, choices, answer_idx = self.format_example(example)
            pred_idx = self._choice_logprob(model, tokenizer, prompt, choices, device)
            if pred_idx == answer_idx:
                correct += 1
            total += 1
        if total == 0:
            return self._synthetic_run(model, tokenizer, device)
        score = correct / total
        stderr = math.sqrt(score * (1 - score) / total) if total > 0 else 0.0
        return BenchmarkResult(name=self.name(), score=score, stderr=stderr, metadata={"n_samples": total})

    def name(self) -> str:
        return self.dataset_name.replace("/", "_").replace("-", "_")

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        raise NotImplementedError


class MMLUBenchmark(MultipleChoiceBenchmark):
    def __init__(self, subject: str = "all", max_samples: int = 1000):
        super().__init__("cais/mmlu", config_name=subject, max_samples=max_samples)

    def format_example(self, example):
        prompt = example["question"] + "\n"
        for i, option in enumerate(example["choices"]):
            prompt += f"({chr(65 + i)}) {option}\n"
        prompt += "Answer:"
        return prompt, example["choices"], int(example["answer"])


class HellaSwagBenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("Rowan/hellaswag", max_samples=max_samples)

    def format_example(self, example):
        ctx = example["ctx"]
        endings = example["endings"]
        prompt = ctx + "\n"
        choices = [str(e) for e in endings]
        answer_idx = int(example["label"])
        return prompt, choices, answer_idx


class ARCBenchmark(MultipleChoiceBenchmark):
    def __init__(self, config_name: str = "ARC-Easy", max_samples: int = 1000):
        super().__init__("allenai/arc", config_name=config_name, max_samples=max_samples)

    def format_example(self, example):
        prompt = example["question"] + "\n"
        for i, option in enumerate(example["choices"]["text"]):
            prompt += f"({chr(65 + i)}) {option}\n"
        prompt += "Answer:"
        answer_label = example["answerKey"]
        choices = example["choices"]["text"]
        answer_idx = choices.index(answer_label) if answer_label in choices else 0
        return prompt, choices, answer_idx


class GSM8KBenchmark(BaseBenchmark):
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples

    def prepare_dataset(self):
        return self._load_dataset("openai/gsm8k", "main", split="test")

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        dataset = self.prepare_dataset()
        if dataset is None:
            return self._synthetic_run(model, tokenizer, device)
        for example in dataset:
            if total >= self.max_samples:
                break
            question = example["question"]
            reference = example["answer"]
            generated = self._generate_text(model, tokenizer, question, device, max_new_tokens=128)
            if self._is_correct_gsm8k(generated, reference):
                correct += 1
            total += 1
        if total == 0:
            return self._synthetic_run(model, tokenizer, device)
        score = correct / total
        stderr = math.sqrt(score * (1 - score) / total) if total > 0 else 0.0
        return BenchmarkResult(name="gsm8k", score=score, stderr=stderr, metadata={"n_samples": total})

    def _is_correct_gsm8k(self, generated: str, reference: str) -> bool:
        ref_answer = re.search(r"####\s*([-\d.,]+)", reference)
        ref_num = float(ref_answer.group(1).replace(",", "")) if ref_answer else None
        if ref_num is None:
            return False
        gen_match = re.search(r"(-?\d+(?:\.\d+)?)", generated.replace(",", ""))
        if not gen_match:
            return False
        gen_num = float(gen_match.group(1))
        return abs(gen_num - ref_num) < 1e-3

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        examples = _SYNTHETIC_GSM8K()
        for q, ref in examples:
            if total >= self.max_samples:
                break
            gen = self._generate_text(model, tokenizer, q, device, max_new_tokens=64)
            if self._is_correct_gsm8k(gen, ref):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="gsm8k_synthetic", score=score, stderr=stderr, metadata={"n_samples": total, "synthetic": True})


class HumanEvalBenchmark(BaseBenchmark):
    def __init__(self, max_samples: int = 164):
        self.max_samples = max_samples

    def prepare_dataset(self):
        return self._load_dataset("openai_humaneval", split="test")

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        dataset = self.prepare_dataset()
        if dataset is None:
            return self._synthetic_run(model, tokenizer, device)
        for example in dataset:
            if total >= self.max_samples:
                break
            prompt = example["prompt"]
            reference = example["canonical_solution"]
            generated = self._generate_text(model, tokenizer, prompt, device, max_new_tokens=256)
            if self._exact_match(generated, reference):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="humaneval", score=score, stderr=stderr, metadata={"n_samples": total})

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        examples = _SYNTHETIC_CODEGEN_HUMANEVAL()
        for prompt, ref in examples:
            if total >= self.max_samples:
                break
            gen = self._generate_text(model, tokenizer, prompt, device, max_new_tokens=128)
            if self._exact_match(gen, ref):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="humaneval_synthetic", score=score, stderr=stderr, metadata={"n_samples": total, "synthetic": True})


class MBPPBenchmark(BaseBenchmark):
    def __init__(self, max_samples: int = 500):
        self.max_samples = max_samples

    def prepare_dataset(self):
        return self._load_dataset("mbpp", split="test")

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        dataset = self.prepare_dataset()
        if dataset is None:
            return self._synthetic_run(model, tokenizer, device)
        for example in dataset:
            if total >= self.max_samples:
                break
            prompt = example["prompt"] + "\n"
            reference = example["code"]
            generated = self._generate_text(model, tokenizer, prompt, device, max_new_tokens=256)
            if self._exact_match(generated, reference):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="mbpp", score=score, stderr=stderr, metadata={"n_samples": total})

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        examples = _SYNTHETIC_CODEGEN_MBPP()
        for prompt, ref in examples:
            if total >= self.max_samples:
                break
            gen = self._generate_text(model, tokenizer, prompt, device, max_new_tokens=128)
            if self._exact_match(gen, ref):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="mbpp_synthetic", score=score, stderr=stderr, metadata={"n_samples": total, "synthetic": True})


class PIQABenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("piqa", max_samples=max_samples)

    def format_example(self, example):
        prompt = example["goal"] + "\n"
        choices = [example["sol1"], example["sol2"]]
        answer_idx = int(example["label"])
        return prompt, choices, answer_idx


class BoolQBenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("boolq", max_samples=max_samples)

    def format_example(self, example):
        prompt = example["question"] + "\n" + example["passage"] + "\n"
        choices = ["No", "Yes"]
        answer_idx = 1 if example["answer"] else 0
        return prompt, choices, answer_idx


class WinograndeBenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("winogrande", config_name="winogrande_xl", max_samples=max_samples)

    def format_example(self, example):
        sentence = example["sentence"]
        options = [example["option1"], example["option2"]]
        prompt = sentence.replace("_", "{}")
        answer_idx = int(example["answer"]) - 1
        return prompt, options, answer_idx


class SyntheticMMLUBenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("synthetic_mmlu", max_samples=max_samples)

    def prepare_dataset(self):
        return iter(_SYNTHETIC_MMLU())

    def format_example(self, example):
        prompt = example["question"] + "\n"
        for i, option in enumerate(example["choices"]):
            prompt += f"({chr(65 + i)}) {option}\n"
        prompt += "Answer:"
        return prompt, example["choices"], example["answer"]

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        return self.run(model, tokenizer, device)


class SyntheticHellaSwagBenchmark(MultipleChoiceBenchmark):
    def __init__(self, max_samples: int = 1000):
        super().__init__("synthetic_hellaswag", max_samples=max_samples)

    def prepare_dataset(self):
        return iter(_SYNTHETIC_HELLASWAG())

    def format_example(self, example):
        prompt = example["ctx"] + "\n"
        choices = example["endings"]
        return prompt, choices, example["label"]

    def _synthetic_run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        return self.run(model, tokenizer, device)


class SyntheticGSM8KBenchmark(BaseBenchmark):
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples

    def prepare_dataset(self):
        return iter(_SYNTHETIC_GSM8K())

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        for question, reference in self.prepare_dataset():
            if total >= self.max_samples:
                break
            generated = self._generate_text(model, tokenizer, question, device, max_new_tokens=128)
            if self._is_correct_gsm8k(generated, reference):
                correct += 1
            total += 1
        score = correct / total if total else 0.0
        stderr = math.sqrt(score * (1 - score) / total) if total else 0.0
        return BenchmarkResult(name="gsm8k_synthetic", score=score, stderr=stderr, metadata={"n_samples": total, "synthetic": True})

    def _is_correct_gsm8k(self, generated: str, reference: str) -> bool:
        ref_answer = re.search(r"####\s*([-\d.,]+)", reference)
        ref_num = float(ref_answer.group(1).replace(",", "")) if ref_answer else None
        if ref_num is None:
            return False
        gen_match = re.search(r"(-?\d+(?:\.\d+)?)", generated.replace(",", ""))
        if not gen_match:
            return False
        gen_num = float(gen_match.group(1))
        return abs(gen_num - ref_num) < 1e-3


class EvaluationHarness:
    def __init__(self, model, tokenizer, model_name: str = "model", device: str = "cpu"):
        self.model = model
        self.tokenizer = tokenizer
        self.model_name = model_name
        self.device = device

    def run_benchmark(self, name: str, max_samples: int = 1000) -> BenchmarkResult:
        benchmark = get_benchmark(name, max_samples=max_samples)
        return benchmark.run(self.model, self.tokenizer, device=self.device)

    def evaluate(self, benchmark_names: List[str], max_samples: int = 1000, output_path: Optional[str] = None) -> Dict[str, Any]:
        results: Dict[str, BenchmarkResult] = {}
        for name in benchmark_names:
            try:
                results[name] = self.run_benchmark(name, max_samples=max_samples)
            except Exception as exc:
                results[name] = BenchmarkResult(name=name, score=0.0, stderr=0.0, metadata={"error": str(exc)})
        report = {
            "model_name": self.model_name,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {k: v.to_dict() for k, v in results.items()},
            "summary": self._summary(results),
        }
        if output_path:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        return report

    def quick_eval(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        return self.evaluate(
            ["mmlu", "hellaswag", "arc", "gsm8k", "humaneval", "mbpp", "piqa", "boolq", "winogrande"],
            max_samples=500,
            output_path=output_path,
        )

    def _summary(self, results: Dict[str, BenchmarkResult]) -> str:
        lines = [f"Evaluation Report - {self.model_name} ({datetime.utcnow().isoformat()}Z)"]
        for name, result in results.items():
            lines.append(f"  {name}: {result.score:.4f} ± {result.stderr:.4f}")
        return "\n".join(lines)


BENCHMARK_REGISTRY: Dict[str, type] = {
    "mmlu": MMLUBenchmark,
    "hellaswag": HellaSwagBenchmark,
    "arc": ARCBenchmark,
    "gsm8k": GSM8KBenchmark,
    "humaneval": HumanEvalBenchmark,
    "mbpp": MBPPBenchmark,
    "piqa": PIQABenchmark,
    "boolq": BoolQBenchmark,
    "winogrande": WinograndeBenchmark,
    "synthetic_mmlu": SyntheticMMLUBenchmark,
    "synthetic_hellaswag": SyntheticHellaSwagBenchmark,
    "synthetic_gsm8k": SyntheticGSM8KBenchmark,
}


def get_benchmark(name: str, **kwargs) -> BaseBenchmark:
    if name not in BENCHMARK_REGISTRY:
        raise KeyError(f"Unknown benchmark: {name}. Available: {list(BENCHMARK_REGISTRY.keys())}")
    return BENCHMARK_REGISTRY[name](**kwargs)


def _SYNTHETIC_MMLU() -> List[Dict[str, Any]]:
    subjects = {
        "sci": ("What is the chemical symbol for water?", ["CO2", "H2O", "NaCl", "O2"], 1),
        "hist": ("Who was the first President of the United States?", ["Lincoln", "Washington", "Adams", "Jefferson"], 1),
        "math": ("What is 2 + 2?", ["3", "4", "5", "6"], 1),
        "bio": ("What organ pumps blood?", ["Brain", "Heart", "Lung", "Liver"], 1),
        "phys": ("What force keeps planets in orbit?", ["Friction", "Gravity", "Magnetism", "Tension"], 1),
    }
    out = []
    for _ in range(20):
        q, choices, ans = random.choice(list(subjects.values()))
        out.append({"question": q, "choices": choices, "answer": ans, "subject": "synthetic"})
    return out


def _SYNTHETIC_HELLASWAG() -> List[Dict[str, Any]]:
    items = [
        {"ctx": "The chef chopped the onions.", "endings": ["and cried.", "and slept.", "and sang.", "and ran."], "label": 0},
        {"ctx": "The student opened the book.", "endings": ["and read.", "and ate it.", "and threw it.", "and hid it."], "label": 0},
        {"ctx": "The dog barked at the mailman.", "endings": ["and ran away.", "and flew.", "and teleported.", "and read."], "label": 0},
    ]
    out = []
    for _ in range(20):
        item = random.choice(items)
        out.append(dict(item))
    return out


def _SYNTHETIC_GSM8K() -> List[Tuple[str, str]]:
    problems = [
        ("If a train travels 60 miles per hour for 2 hours, how many miles does it travel?", "#### 120"),
        ("A bakery sells 30 loaves of bread each day. How many loaves in 5 days?", "#### 150"),
        ("What is 15 + 27?", "#### 42"),
        ("If you have 50 apples and give away 12, how many remain?", "#### 38"),
        ("A car uses 4 gallons of gas to travel 100 miles. How far with 12 gallons?", "#### 300"),
    ]
    out = []
    for _ in range(20):
        q, a = random.choice(problems)
        out.append((q, a))
    return out


def _SYNTHETIC_CODEGEN_HUMANEVAL() -> List[Tuple[str, str]]:
    return [
        ("def add(a, b):\n", "    return a + b\n"),
        ("def factorial(n):\n", "    return 1 if n == 0 else n * factorial(n-1)\n"),
        ("def is_palindrome(s):\n", "    return s == s[::-1]\n"),
    ]


def _SYNTHETIC_CODEGEN_MBPP() -> List[Tuple[str, str]]:
    return [
        ("Write a function that returns the square of a number.\n", "def square(n):\n    return n * n\n"),
        ("Write a function that checks if a number is even.\n", "def is_even(n):\n    return n % 2 == 0\n"),
        ("Write a function that returns the maximum of two numbers.\n", "def max_two(a, b):\n    return a if a > b else b\n"),
    ]
