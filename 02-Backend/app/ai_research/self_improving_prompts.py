"""Self-improving prompt optimizer using feedback and A/B testing."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PromptVariant:
    id: str
    template: str
    score: float = 0.0
    uses: int = 0


class SelfImprovingPromptOptimizer:
    def __init__(self) -> None:
        self._client = None
        self.variants: dict[str, list[PromptVariant]] = {}

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register(self, prompt_id: str, template: str) -> PromptVariant:
        variant = PromptVariant(id=str(uuid.uuid4()), template=template)
        self.variants.setdefault(prompt_id, []).append(variant)
        return variant

    def record_feedback(self, prompt_id: str, variant_id: str, score: float) -> None:
        for variant in self.variants.get(prompt_id, []):
            if variant.id == variant_id:
                total = variant.score * variant.uses + score
                variant.uses += 1
                variant.score = total / variant.uses
                break

    def best(self, prompt_id: str) -> PromptVariant | None:
        variants = self.variants.get(prompt_id)
        if not variants:
            return None
        return max(variants, key=lambda v: v.score / max(v.uses, 1))

    def optimize(self, prompt_id: str, feedback: list[tuple[str, float]]) -> PromptVariant:
        current = self.best(prompt_id)
        template = current.template if current else ""
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Improve the prompt to increase helpfulness and accuracy."},
                    {"role": "user", "content": f"Current prompt:\n{template}\n\nFeedbacks: {feedback}\n\nReturn improved prompt only."},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            improved = result.choices[0].message.content or template
        except Exception as exc:
            logger.error("Prompt optimization failed: %s", exc)
            improved = template
        return self.register(f"{prompt_id}:optimized:{len(self.variants.get(prompt_id, []))}", improved)
