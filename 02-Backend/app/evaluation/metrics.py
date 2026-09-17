import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCalculator:
    def calculate(self, output: str, prompt: str, expected: str | None = None) -> dict[str, Any]:
        tokens = len(output.split())
        coherence = self._coherence_score(output)
        relevance = self._relevance_score(output, prompt)
        accuracy = 1.0 if expected and output.strip() == expected.strip() else 0.0
        return {
            "tokens": tokens,
            "coherence": coherence,
            "relevance": relevance,
            "accuracy": accuracy,
        }

    def _coherence_score(self, text: str) -> float:
        sentences = re.split(r'[.!?]', text)
        if not sentences:
            return 0.0
        return min(len(sentences) / 10, 1.0)

    def _relevance_score(self, output: str, prompt: str) -> float:
        prompt_words = set(prompt.lower().split())
        output_words = set(output.lower().split())
        if not prompt_words:
            return 0.0
        overlap = prompt_words & output_words
        return len(overlap) / len(prompt_words)
