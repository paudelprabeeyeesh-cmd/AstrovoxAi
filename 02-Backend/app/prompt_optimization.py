"""Automatic prompt optimization using evaluation feedback."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PromptVariant:
    id: str
    template: str
    score: float = 0.0
    uses: int = 0


class PromptOptimizer:
    def __init__(self) -> None:
        self._client = None
        self._variants: dict[str, list[PromptVariant]] = {}

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register(self, prompt_id: str, template: str) -> PromptVariant:
        variant = PromptVariant(id=prompt_id, template=template)
        self._variants.setdefault(prompt_id, []).append(variant)
        return variant

    def select_best(self, prompt_id: str) -> PromptVariant | None:
        variants = self._variants.get(prompt_id)
        if not variants:
            return None
        return max(variants, key=lambda v: v.score / max(v.uses, 1))

    def record_feedback(self, prompt_id: str, variant_id: str, score: float) -> None:
        variants = self._variants.get(prompt_id, [])
        for variant in variants:
            if variant.id == variant_id:
                total = variant.score * variant.uses + score
                variant.uses += 1
                variant.score = total / variant.uses
                break

    def optimize(self, prompt_id: str, base_template: str, feedbacks: list[tuple[str, float]]) -> PromptVariant:
        best = self.select_best(prompt_id)
        current_template = best.template if best else base_template
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Improve the prompt to increase helpfulness and accuracy based on feedback scores."},
                    {"role": "user", "content": f"Current prompt:\n{current_template}\n\nFeedbacks: {feedbacks}\n\nReturn an improved prompt only."},
                ],
                temperature=0.2,
                max_tokens=512,
            )
            improved = result.choices[0].message.content or current_template
        except Exception as exc:
            logger.error("Prompt optimization failed: %s", exc)
            improved = current_template
        variant = self.register(f"{prompt_id}:optimized:{len(self._variants.get(prompt_id, []))}", improved)
        return variant
