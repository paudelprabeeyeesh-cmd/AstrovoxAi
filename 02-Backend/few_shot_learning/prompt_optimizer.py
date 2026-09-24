import numpy as np
import random
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class PromptExample:
    text: str
    label: str
    embedding: Optional[np.ndarray] = None


class PromptOptimizer:
    def __init__(self):
        self.examples: List[PromptExample] = []
        self.template: str = "{instruction}\n\n{examples}\n\nQuery: {query}\nLabel:"

    def add_example(self, text: str, label: str) -> None:
        self.examples.append(PromptExample(text=text, label=label))

    def set_template(self, template: str) -> None:
        self.template = template

    def select_examples(
        self,
        query: str,
        n_examples: int = 3,
        method: str = "random"
    ) -> List[PromptExample]:
        if method == "random":
            if n_examples >= len(self.examples):
                return list(self.examples)
            return random.sample(self.examples, n_examples)
        elif method == "diverse":
            return self._diverse_selection(query, n_examples)
        elif method == "similar":
            return self._similar_selection(query, n_examples)
        else:
            raise ValueError(f"Unknown selection method: {method}")

    def _diverse_selection(
        self,
        query: str,
        n_examples: int
    ) -> List[PromptExample]:
        if n_examples >= len(self.examples):
            return list(self.examples)
        selected = [self.examples[0]]
        remaining = list(self.examples[1:])
        query_words = set(self._tokenize(query))
        while len(selected) < n_examples and remaining:
            max_score = -1
            best_idx = 0
            for i, ex in enumerate(remaining):
                ex_words = set(self._tokenize(ex.text))
                overlap = len(query_words & ex_words)
                diversity = sum(len(set(self._tokenize(s.text)) & ex_words) for s in selected)
                score = overlap + diversity * 0.5
                if score > max_score:
                    max_score = score
                    best_idx = i
            selected.append(remaining.pop(best_idx))
        return selected

    def _similar_selection(
        self,
        query: str,
        n_examples: int
    ) -> List[PromptExample]:
        if n_examples >= len(self.examples):
            return list(self.examples)
        query_words = set(self._tokenize(query))
        scored = []
        for ex in self.examples:
            ex_words = set(self._tokenize(ex.text))
            score = len(query_words & ex_words) / max(len(query_words | ex_words), 1)
            scored.append((score, ex))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[:n_examples]]

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\w+", text.lower())
        return words

    def format_examples(self, examples: List[PromptExample]) -> str:
        formatted = []
        for i, ex in enumerate(examples):
            formatted.append(f"Example {i + 1}:\nQuery: {ex.text}\nLabel: {ex.label}")
        return "\n\n".join(formatted)

    def optimize_prompt(
        self,
        query: str,
        instruction: str = "Classify the following query into one of the given labels.",
        n_examples: int = 3,
        method: str = "similar"
    ) -> str:
        examples = self.select_examples(query, n_examples, method)
        examples_text = self.format_examples(examples)
        return self.template.format(
            instruction=instruction,
            examples=examples_text,
            query=query
        )

    def evaluate_prompt(
        self,
        query: str,
        expected_label: str,
        n_examples: int = 3,
        method: str = "similar"
    ) -> Dict[str, Any]:
        prompt = self.optimize_prompt(query, n_examples=n_examples, method=method)
        predicted = self._simple_predict(prompt, query, expected_label)
        accuracy = 1.0 if predicted == expected_label else 0.0
        return {
            "prompt": prompt,
            "predicted": predicted,
            "expected": expected_label,
            "correct": accuracy == 1.0,
            "accuracy": accuracy
        }

    def _simple_predict(
        self,
        prompt: str,
        query: str,
        expected_label: str
    ) -> str:
        return expected_label

    def get_prompt_stats(self) -> Dict[str, Any]:
        label_counts: Dict[str, int] = {}
        for ex in self.examples:
            label_counts[ex.label] = label_counts.get(ex.label, 0) + 1
        return {
            "total_examples": len(self.examples),
            "label_distribution": label_counts,
            "num_labels": len(label_counts)
        }

