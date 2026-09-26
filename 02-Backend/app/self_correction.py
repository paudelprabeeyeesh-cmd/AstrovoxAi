"""Self-correction loop for AI responses."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SelfCorrectionResult:
    original: str
    corrected: str
    confidence: float
    issues: list[str]


class SelfCorrectionLoop:
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def review(self, response: str, context: str | None = None) -> SelfCorrectionResult:
        issues = self._detect_issues(response, context)
        if not issues:
            return SelfCorrectionResult(original=response, corrected=response, confidence=1.0, issues=[])
        corrected = self._apply_corrections(response, issues, context)
        confidence = max(0.0, 1.0 - (len(issues) * 0.2))
        return SelfCorrectionResult(original=response, corrected=corrected, confidence=confidence, issues=issues)

    def _detect_issues(self, response: str, context: str | None = None) -> list[str]:
        issues: list[str] = []
        if not response or not response.strip():
            issues.append("empty_response")
        if len(response) > 4000:
            issues.append("too_long")
        if context and response.strip() not in context:
            issues.append("unsupported_claim")
        return issues

    def _apply_corrections(self, response: str, issues: list[str], context: str | None = None) -> str:
        if "empty_response" in issues:
            return "I couldn't generate a response. Please try again."
        if "too_long" in issues:
            return response[:4000] + "..."
        if "unsupported_claim" in issues and context:
            try:
                client = self._get_client()
                result = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[
                        {"role": "system", "content": "Revise the response so every claim is supported by the context. If unsupported, remove it."},
                        {"role": "user", "content": f"Context:\n{context}\n\nResponse:\n{response}"},
                    ],
                    temperature=0.0,
                    max_tokens=1024,
                )
                return result.choices[0].message.content or response
            except Exception as exc:
                logger.error("Self-correction failed: %s", exc)
        return response
