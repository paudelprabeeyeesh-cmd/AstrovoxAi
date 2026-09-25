"""Prompt template validation for system and user prompts."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class PromptValidationError:
    field: str
    message: str
    severity: str = "error"


@dataclass
class PromptValidationResult:
    valid: bool
    errors: list[PromptValidationError] = field(default_factory=list)
    warnings: list[PromptValidationError] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class PromptTemplateValidator:
    MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
    MAX_VARIABLE_NAME_LENGTH = 64
    MAX_SYSTEM_PROMPT_LENGTH = int(os.getenv("MAX_SYSTEM_PROMPT_LENGTH", "4000"))
    ALLOWED_VARIABLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

    def validate(self, template: str, context: Optional[dict[str, Any]] = None) -> PromptValidationResult:
        errors: list[PromptValidationError] = []
        warnings: list[PromptValidationError] = []
        context = context or {}
        if not isinstance(template, str):
            errors.append(PromptValidationError(field="template", message="Template must be a string"))
            return PromptValidationResult(valid=False, errors=errors, warnings=warnings)
        if len(template) == 0:
            errors.append(PromptValidationError(field="template", message="Template cannot be empty"))
        elif len(template) > self.MAX_PROMPT_LENGTH:
            errors.append(PromptValidationError(
                field="template",
                message=f"Prompt exceeds max length of {self.MAX_PROMPT_LENGTH} characters (got {len(template)})",
            ))
        variables = self._extract_variables(template)
        if variables:
            for var in variables:
                if len(var) > self.MAX_VARIABLE_NAME_LENGTH:
                    errors.append(PromptValidationError(
                        field="variable",
                        message=f"Variable name '{var}' exceeds max length of {self.MAX_VARIABLE_NAME_LENGTH}",
                    ))
                if not self.ALLOWED_VARIABLE_PATTERN.match(var):
                    errors.append(PromptValidationError(
                        field="variable",
                        message=f"Variable name '{var}' contains invalid characters",
                    ))
            for var in variables:
                if var not in context:
                    warnings.append(PromptValidationError(
                        field="variable",
                        message=f"Variable '{var}' is referenced in template but not provided in context",
                        severity="warning",
                    ))
            for key in context:
                if key not in variables:
                    warnings.append(PromptValidationError(
                        field="variable",
                        message=f"Context key '{key}' is not used in template",
                        severity="warning",
                    ))
        if self._detect_injection_risk(template):
            warnings.append(PromptValidationError(
                field="template",
                message="Template may contain prompt injection patterns",
                severity="warning",
            ))
        return PromptValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={
                "variable_count": len(variables),
                "template_length": len(template),
                "context_keys": list(context.keys()),
            },
        )

    def validate_system_prompt(self, prompt: str) -> PromptValidationResult:
        errors: list[PromptValidationError] = []
        warnings: list[PromptValidationError] = []
        if not isinstance(prompt, str):
            errors.append(PromptValidationError(field="system_prompt", message="System prompt must be a string"))
            return PromptValidationResult(valid=False, errors=errors, warnings=warnings)
        if len(prompt) > self.MAX_SYSTEM_PROMPT_LENGTH:
            errors.append(PromptValidationError(
                field="system_prompt",
                message=f"System prompt exceeds max length of {self.MAX_SYSTEM_PROMPT_LENGTH} characters (got {len(prompt)})",
            ))
        if self._detect_injection_risk(prompt):
            warnings.append(PromptValidationError(
                field="system_prompt",
                message="System prompt contains suspicious patterns",
                severity="warning",
            ))
        return PromptValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metadata={"length": len(prompt)},
        )

    def render(self, template: str, context: dict[str, Any]) -> str:
        result = template
        for key, value in context.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        unresolved = re.findall(r"\{([^}]+)\}", result)
        for var in unresolved:
            logger.warning("Unresolved template variable: %s", var)
        return result

    def _extract_variables(self, template: str) -> list[str]:
        return re.findall(r"\{([^}]+)\}", template)

    def _detect_injection_risk(self, text: str) -> bool:
        patterns = [
            r"ignore\s+(previous|above|all)\s+instructions?",
            r"you\s+are\s+now\s+a\s+different",
            r"act\s+as\s+if\s+you\s+are",
            r"new\s+instruction",
            r"forget\s+your\s+role",
            r"bypass\s+filter",
            r"jailbreak",
            r"DAN\s+mode",
        ]
        lower = text.lower()
        return any(re.search(p, lower, re.IGNORECASE) for p in patterns)
