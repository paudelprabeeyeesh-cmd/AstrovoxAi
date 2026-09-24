"""Self-correction loop for AI responses."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.config import settings
from app.intelligence.execution_tracer import ExecutionTracer

logger = logging.getLogger(__name__)


@dataclass
class SelfCorrectionResult:
    original: str
    corrected: str
    confidence: float
    issues: List[str]
    passes: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class SelfCorrectionLoop:
    def __init__(
        self,
        review_model: str = "gpt-4o-mini-2024-07-18",
        max_passes: int = 3,
        tracer: Optional[ExecutionTracer] = None,
    ) -> None:
        self._client = None
        self.review_model = review_model
        self.max_passes = max_passes
        self.tracer = tracer

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def review(
        self,
        response: str,
        context: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> SelfCorrectionResult:
        current = response
        issues: List[str] = []
        passes = 0

        for pass_number in range(1, self.max_passes + 1):
            issues = self._detect_issues(current, context)
            if not issues:
                if self.tracer and request_id:
                    self.tracer.trace_self_correction(
                        request_id=request_id,
                        pass_number=pass_number,
                        issues=issues,
                        corrected=False,
                    )
                return SelfCorrectionResult(
                    original=response,
                    corrected=current,
                    confidence=self._confidence_from_issues(issues, current),
                    issues=issues,
                    passes=passes,
                )

            corrected = self._apply_corrections(current, issues, context)
            passes = pass_number
            if self.tracer and request_id:
                self.tracer.trace_self_correction(
                    request_id=request_id,
                    pass_number=pass_number,
                    issues=issues,
                    corrected=True,
                )
            if corrected == current:
                break
            current = corrected

        confidence = self._confidence_from_issues(issues, current)
        return SelfCorrectionResult(
            original=response,
            corrected=current,
            confidence=confidence,
            issues=issues,
            passes=passes,
            metadata={"max_passes": self.max_passes},
        )

    def _detect_issues(self, response: str, context: Optional[str] = None) -> List[str]:
        issues: List[str] = []
        if not response or not response.strip():
            issues.append("empty_response")
        if len(response) > 4000:
            issues.append("too_long")
        if context and response.strip() not in context:
            issues.append("unsupported_claim")
        return issues

    def _apply_corrections(self, response: str, issues: List[str], context: Optional[str] = None) -> str:
        if "empty_response" in issues:
            return "I couldn't generate a response. Please try again."
        if "too_long" in issues:
            return response[:4000] + "..."
        if "unsupported_claim" in issues and context:
            try:
                client = self._get_client()
                result = client.chat.completions.create(
                    model=self.review_model,
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

    def _confidence_from_issues(self, issues: List[str], response: str) -> float:
        if not issues:
            return 1.0
        if not response or not response.strip():
            return 0.0
        penalty = len(issues) * 0.2
        return max(0.0, 1.0 - penalty)
