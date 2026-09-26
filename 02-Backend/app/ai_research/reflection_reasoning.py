"""Reflection-based reasoning with self-critique and improvement."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReflectionResult:
    original: str
    critique: str
    improved: str
    confidence: float


class ReflectionReasoning:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def reflect(self, response: str, context: str | None = None) -> ReflectionResult:
        critique = self._critique(response, context)
        improved = self._improve(response, critique, context)
        confidence = self._confidence(improved, critique)
        return ReflectionResult(original=response, critique=critique, improved=improved, confidence=confidence)

    def _critique(self, response: str, context: str | None) -> str:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Critique the response for correctness, completeness, and clarity. Be concise."},
                    {"role": "user", "content": f"Response:\n{response}\n\nContext:\n{context or 'None'}"},
                ],
                temperature=0.0,
                max_tokens=256,
            )
            return result.choices[0].message.content or ""
        except Exception as exc:
            logger.error("Reflection critique failed: %s", exc)
            return ""

    def _improve(self, response: str, critique: str, context: str | None) -> str:
        try:
            client = self._get_client()
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Rewrite the response to address the critique. Keep it concise and accurate."},
                    {"role": "user", "content": f"Original:\n{response}\n\nCritique:\n{critique}\n\nContext:\n{context or 'None'}"},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            return result.choices[0].message.content or response
        except Exception as exc:
            logger.error("Reflection improvement failed: %s", exc)
            return response

    def _confidence(self, improved: str, critique: str) -> float:
        if not improved or not improved.strip():
            return 0.0
        base = 0.5
        if critique and "issue" in critique.lower():
            base -= 0.2
        if len(improved.split()) > 200:
            base -= 0.1
        return max(0.0, min(1.0, base))
