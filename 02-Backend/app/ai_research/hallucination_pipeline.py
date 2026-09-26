"""Automatic benchmark generation and hallucination reduction pipeline."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkCase:
    id: str
    prompt: str
    expected_facts: list[str]
    provider: str
    model: str


class AutomaticBenchmarkGenerator:
    def generate(self, source_text: str, count: int = 10) -> list[BenchmarkCase]:
        cases: list[BenchmarkCase] = []
        facts = self._extract_facts(source_text)
        for idx in range(min(count, len(facts))):
            cases.append(
                BenchmarkCase(
                    id=str(uuid.uuid4()),
                    prompt=f"Based on the documentation, answer: {facts[idx]}",
                    expected_facts=[facts[idx]],
                    provider="openai",
                    model="gpt-4o-mini-2024-07-18",
                )
            )
        return cases

    def _extract_facts(self, text: str) -> list[str]:
        sentences = [segment.strip() for segment in text.replace("\n", " ").split(".") if segment.strip()]
        return sentences[:20]


class HallucinationReductionPipeline:
    def reduce(self, response: str, context: str) -> str:
        unsupported = self._find_unsupported(response, context)
        if not unsupported:
            return response
        try:
            import openai
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            result = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Remove claims not supported by the context."},
                    {"role": "user", "content": f"Context:\n{context}\n\nResponse:\n{response}\n\nUnsupported claims:\n{unsupported}"},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            return result.choices[0].message.content or response
        except Exception as exc:
            logger.error("Hallucination reduction failed: %s", exc)
            return response

    def _find_unsupported(self, response: str, context: str) -> list[str]:
        claims: list[str] = []
        lower_context = context.lower()
        for segment in response.split("\n"):
            segment = segment.strip()
            if not segment:
                continue
            keywords = [word.lower() for word in segment.split() if len(word) > 5][:5]
            if keywords and not any(keyword in lower_context for keyword in keywords):
                claims.append(segment)
        return claims
