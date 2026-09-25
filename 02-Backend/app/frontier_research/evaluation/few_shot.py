"""Few-shot and zero-shot evaluation harness."""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EvaluationExample:
    prompt: str
    reference: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    example_id: str
    predicted: str
    score: float = 0.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class FewShotEvaluator:
    def __init__(self, num_shots: int = 3, max_tokens: int = 256, temperature: float = 0.0):
        self.num_shots = num_shots
        self.max_tokens = max_tokens
        self.temperature = temperature

    def build_prompt(self, examples: list[EvaluationExample], target: str) -> str:
        lines: list[str] = []
        for example in examples[: self.num_shots]:
            lines.append(f"Input: {example.prompt}")
            if example.reference:
                lines.append(f"Output: {example.reference}")
        lines.append(f"Input: {target}")
        lines.append("Output:")
        return "\n".join(lines)

    def evaluate(self, model: Any, dataset: list[EvaluationExample]) -> list[EvalResult]:
        results: list[EvalResult] = []
        for example in dataset:
            start = time.perf_counter()
            prompt = self.build_prompt(dataset, example.prompt)
            predicted = self._call_model(model, prompt)
            latency = (time.perf_counter() - start) * 1000
            score = self._score(example.reference, predicted)
            results.append(
                EvalResult(
                    example_id=str(uuid.uuid4()),
                    predicted=predicted,
                    score=score,
                    latency_ms=latency,
                    metadata={"prompt_length": len(prompt)},
                )
            )
        return results

    def _call_model(self, model: Any, prompt: str) -> str:
        if hasattr(model, "generate"):
            return model.generate(prompt, max_tokens=self.max_tokens, temperature=self.temperature)
        if callable(model):
            return str(model(prompt))
        return ""

    def _score(self, reference: str | None, predicted: str) -> float:
        if not reference:
            return 0.0
        ref = reference.strip().lower()
        pred = predicted.strip().lower()
        if not pred:
            return 0.0
        return 1.0 if ref in pred else 0.0


class ZeroShotEvaluator(FewShotEvaluator):
    def __init__(self, max_tokens: int = 256, temperature: float = 0.0):
        super().__init__(num_shots=0, max_tokens=max_tokens, temperature=temperature)

    def build_prompt(self, examples: list[EvaluationExample], target: str) -> str:
        return f"{target}\n\nAnswer concisely:"
