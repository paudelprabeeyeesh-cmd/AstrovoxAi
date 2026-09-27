import os
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import torch
from torch.utils.data import DataLoader, Dataset


@dataclass
class BenchmarkResult:
    name: str
    score: float
    stderr: float
    metadata: Dict[str, Any]


class PerplexityBenchmark:
    def __init__(self, tokenizer, max_batches: int = 100):
        self.tokenizer = tokenizer
        self.max_batches = max_batches

    def prepare_dataset(self, split: str = "validation"):
        from datasets import load_dataset
        ds = load_dataset("wikimedia/wikipedia", "20231101.en", split=split, streaming=True)
        return ds

    def run(self, model, device: str = "cpu") -> BenchmarkResult:
        model.eval()
        total_loss = 0.0
        total_tokens = 0
        count = 0
        with torch.no_grad():
            for example in self.prepare_dataset():
                enc = self.tokenizer(example["text"], truncation=True, max_length=512, return_tensors="pt")
                input_ids = enc.input_ids.to(device)
                labels = input_ids.clone()
                outputs = model(input_ids, labels=labels)
                loss = outputs["loss"]
                if loss is None:
                    continue
                total_loss += loss.item() * input_ids.numel()
                total_tokens += input_ids.numel()
                count += 1
                if count >= self.max_batches:
                    break
        model.train()
        if total_tokens == 0:
            return BenchmarkResult(name="perplexity", score=float("inf"), stderr=0.0, metadata={})
        avg_loss = total_loss / total_tokens
        return BenchmarkResult(name="perplexity", score=math.exp(avg_loss), stderr=0.0, metadata={"n_batches": count})


class MultipleChoiceBenchmark:
    def __init__(self, dataset_name: str, config_name: Optional[str] = None, split: str = "test", max_samples: int = 1000):
        self.dataset_name = dataset_name
        self.config_name = config_name
        self.split = split
        self.max_samples = max_samples

    def prepare_dataset(self):
        from datasets import load_dataset
        if self.config_name:
            return load_dataset(self.dataset_name, self.config_name, split=self.split, streaming=True)
        return load_dataset(self.dataset_name, split=self.split, streaming=True)

    def format_example(self, example: Dict[str, Any]) -> Tuple[str, List[str], int]:
        raise NotImplementedError

    def compute_choice_logprob(self, model, tokenizer, prompt: str, choices: List[str], device: str) -> float:
        scores = []
        for choice in choices:
            enc = tokenizer(prompt + " " + choice, truncation=True, max_length=512, return_tensors="pt")
            input_ids = enc.input_ids.to(device)
            labels = input_ids.clone()
            with torch.no_grad():
                outputs = model(input_ids, labels=labels)
                loss = outputs["loss"]
            scores.append(-loss.item() * input_ids.numel() if loss is not None else float("-inf"))
        return scores.index(max(scores))

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        for example in self.prepare_dataset():
            if total >= self.max_samples:
                break
            prompt, choices, answer_idx = self.format_example(example)
            pred_idx = self.compute_choice_logprob(model, tokenizer, prompt, choices, device)
            if pred_idx == answer_idx:
                correct += 1
            total += 1
        if total == 0:
            return BenchmarkResult(name=self.dataset_name, score=0.0, stderr=0.0, metadata={})
        score = correct / total
        stderr = math.sqrt(score * (1 - score) / total)
        return BenchmarkResult(name=self.dataset_name, score=score, stderr=stderr, metadata={"n_samples": total})


class MMLUBenchmark(MultipleChoiceBenchmark):
    def __init__(self, subject: str = "all", **kwargs):
        super().__init__("cais/mmlu", config_name=subject, **kwargs)

    def format_example(self, example):
        prompt = example["question"] + "\n"
        for i, option in enumerate(example["choices"]):
            prompt += f"({chr(65+i)}) {option}\n"
        prompt += "Answer:"
        return prompt, example["choices"], example["answer"]


class HellaSwagBenchmark(MultipleChoiceBenchmark):
    def __init__(self, **kwargs):
        super().__init__("Rowan/hellaswag", **kwargs)

    def format_example(self, example):
        ctx = example["ctx"]
        endings = example["endings"]
        prompt = ctx + "\n"
        choices = []
        for ending in endings:
            choices.append(ending)
        answer_idx = int(example["label"])
        return prompt, choices, answer_idx


class WinoGrandeBenchmark(MultipleChoiceBenchmark):
    def __init__(self, **kwargs):
        super().__init__("winogrande", config_name="winogrande_xl", **kwargs)

    def format_example(self, example):
        sentence = example["sentence"]
        options = [example["option1"], example["option2"]]
        prompt = sentence.replace("_", "{{}}")
        answer_idx = int(example["answer"]) - 1
        return prompt, options, answer_idx


class TruthfulQABenchmark:
    def __init__(self, max_samples: int = 500):
        self.max_samples = max_samples

    def prepare_dataset(self):
        from datasets import load_dataset
        return load_dataset("truthful_qa", "generation", split="validation", streaming=True)

    def run(self, model, tokenizer, device: str = "cpu") -> BenchmarkResult:
        correct = 0
        total = 0
        for example in self.prepare_dataset():
            if total >= self.max_samples:
                break
            question = example["question"]
            reference = example["best_answer"]
            generated = self._generate_answer(model, tokenizer, question, device)
            if self._is_correct(generated, reference):
                correct += 1
            total += 1
        if total == 0:
            return BenchmarkResult(name="truthfulqa", score=0.0, stderr=0.0, metadata={})
        score = correct / total
        stderr = math.sqrt(score * (1 - score) / total)
        return BenchmarkResult(name="truthfulqa", score=score, stderr=stderr, metadata={"n_samples": total})

    def _generate_answer(self, model, tokenizer, question: str, device: str, max_new_tokens: int = 64) -> str:
        enc = tokenizer(question, truncation=True, max_length=256, return_tensors="pt").to(device)
        model.eval()
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0][enc.input_ids.shape[1]:], skip_special_tokens=True)

    def _is_correct(self, generated: str, reference: str) -> bool:
        ref_words = set(reference.lower().split())
        gen_words = set(generated.lower().split())
        if not ref_words:
            return False
        overlap = ref_words & gen_words
        return len(overlap) / len(ref_words) >= 0.5


BENCHMARK_REGISTRY = {
    "perplexity": PerplexityBenchmark,
    "mmlu": MMLUBenchmark,
    "hellaswag": HellaSwagBenchmark,
    "winogrande": WinoGrandeBenchmark,
    "truthfulqa": TruthfulQABenchmark,
}


def get_benchmark(name: str, **kwargs):
    if name not in BENCHMARK_REGISTRY:
        raise KeyError(f"Unknown benchmark: {name}. Available: {list(BENCHMARK_REGISTRY.keys())}")
    return BENCHMARK_REGISTRY[name](**kwargs)
