"""Constitutional AI and self-critique loops."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ConstitutionRule:
    name: str
    description: str
    severity: str = "medium"


@dataclass
class CritiqueResult:
    rule: ConstitutionRule
    passed: bool
    feedback: str
    revised_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfCritiqueLoop:
    prompt: str
    original_response: str
    critiques: list[CritiqueResult] = field(default_factory=list)
    final_response: str | None = None
    loop_count: int = 0


class ConstitutionalAI:
    def __init__(self, rules: list[ConstitutionRule] | None = None, max_loops: int = 2, model: str = "gpt-4o-mini-2024-07-18"):
        self.rules = rules or []
        self.max_loops = max_loops
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def run(self, prompt: str, response: str) -> SelfCritiqueLoop:
        loop = SelfCritiqueLoop(prompt=prompt, original_response=response)
        current = response
        for _ in range(self.max_loops):
            critiques = self._critique(prompt, current)
            loop.critiques.extend(critiques)
            loop.loop_count += 1
            revised = self._revise(prompt, current, critiques)
            if revised == current:
                break
            current = revised
        loop.final_response = current
        return loop

    def _critique(self, prompt: str, response: str) -> list[CritiqueResult]:
        results: list[CritiqueResult] = []
        try:
            client = self._get_client()
            for rule in self.rules:
                result = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"Evaluate the response against this rule: {rule.description}. Return JSON: passed (bool), feedback (str)."},
                        {"role": "user", "content": f"Prompt:\n{prompt}\n\nResponse:\n{response}"},
                    ],
                    temperature=0.0,
                )
                import json
                content = result.choices[0].message.content or "{}"
                data = json.loads(content)
                results.append(
                    CritiqueResult(
                        rule=rule,
                        passed=bool(data.get("passed", False)),
                        feedback=str(data.get("feedback", "")),
                    )
                )
        except Exception as exc:
            logger.error("Constitutional critique failed: %s", exc)
        return results

    def _revise(self, prompt: str, response: str, critiques: list[CritiqueResult]) -> str:
        failed = [c for c in critiques if not c.passed]
        if not failed:
            return response
        try:
            client = self._get_client()
            feedback = "\n".join(f"- {c.rule.name}: {c.feedback}" for c in failed)
            result = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Revise the response to address the feedback while staying helpful."},
                    {"role": "user", "content": f"Original prompt:\n{prompt}\n\nCurrent response:\n{response}\n\nFeedback:\n{feedback}\n\nRevised:"},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            return result.choices[0].message.content or response
        except Exception as exc:
            logger.error("Constitutional revision failed: %s", exc)
            return response
