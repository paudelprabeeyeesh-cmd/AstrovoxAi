"""Coder agent for code generation."""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CodeArtifact:
    language: str
    code: str
    description: str
    tests: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CoderAgent:
    _artifacts: Dict[str, CodeArtifact] = {}

    @classmethod
    def generate(cls, language: str, description: str, tests: bool = False) -> CodeArtifact:
        code = f"# Generated {language} code for: {description}\ndef solution():\n    return '{description}'\n"
        artifact = CodeArtifact(
            language=language,
            code=code,
            description=description,
            tests="def test_solution():\n    assert solution() is not None\n" if tests else "",
        )
        cls._artifacts[f"{language}:{description}"] = artifact
        return artifact

    @classmethod
    def review(cls, language: str, code: str) -> Dict[str, Any]:
        issues = []
        if "pass" in code:
            issues.append("Code contains pass statement - needs implementation")
        return {
            "language": language,
            "issues": issues,
            "score": 0.5 if issues else 1.0,
        }
