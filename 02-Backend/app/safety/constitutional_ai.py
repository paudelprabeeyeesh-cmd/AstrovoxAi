"""Constitutional AI critique and revision loop."""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class Principle:
    name: str
    description: str
    check: Callable[[str], dict]


@dataclass
class Constitution:
    name: str
    principles: list[Principle]


class ConstitutionalAI:
    def __init__(self, constitution: Constitution):
        self.constitution = constitution

    def critique(self, response: str) -> dict:
        violations = []
        for principle in self.constitution.principles:
            try:
                result = principle.check(response)
                if not result.get("pass", True):
                    violations.append({
                        "principle": principle.name,
                        "reason": result.get("reason", "Violation"),
                        "severity": result.get("severity", "medium"),
                    })
            except Exception as exc:
                logger.error("Principle check failed for %s: %s", principle.name, exc)
        return {
            "violations": violations,
            "revised_response": response,
            "passed": len(violations) == 0,
        }

    def revise(self, response: str) -> dict:
        critique = self.critique(response)
        if critique["passed"]:
            return critique
        revised = response
        for violation in critique["violations"]:
            revised = self._apply_revision(revised, violation)
        critique["revised_response"] = revised
        return critique

    def _apply_revision(self, text: str, violation: dict) -> str:
        principle = violation["principle"]
        if principle == "no_harm":
            return "I cannot provide content that could cause harm."
        if principle == "no_hate":
            return "I strive to be respectful and inclusive."
        if principle == "no_deception":
            return "I aim to be truthful and accurate."
        return text


def make_default_constitution() -> Constitution:
    return Constitution(
        name="default",
        principles=[
            Principle(
                name="no_harm",
                description="Do not cause physical or psychological harm.",
                check=lambda text: {"pass": "harm" not in text.lower(), "reason": "Harmful language detected", "severity": "high"},
            ),
            Principle(
                name="no_hate",
                description="Do not produce hateful or discriminatory content.",
                check=lambda text: {"pass": "hate" not in text.lower(), "reason": "Hateful language detected", "severity": "high"},
            ),
            Principle(
                name="no_deception",
                description="Do not intentionally mislead.",
                check=lambda text: {"pass": "lie" not in text.lower(), "reason": "Deceptive language detected", "severity": "medium"},
            ),
            Principle(
                name="respect_privacy",
                description="Do not disclose private information.",
                check=lambda text: {"pass": "private" not in text.lower() or "respect" in text.lower(), "reason": "Privacy concern", "severity": "high"},
            ),
        ],
    )


constitutional_ai = ConstitutionalAI(make_default_constitution())
