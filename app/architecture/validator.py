from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set


@dataclass
class RuleViolation:
    file: str
    line: int
    rule: str
    detail: str


class ArchitectureRules:
    LAYER_RULES = {
        "app/api/": {"allowed_prefixes": ("app/api/", "app/core/")},
        "app/core/": {"allowed_prefixes": ("app/core/",)},
        "app/services/": {"allowed_prefixes": ("app/services/", "app/core/")},
        "app/plugins/": {"allowed_prefixes": ("app/plugins/", "app/core/")},
    }
    FORBIDDEN_IMPORTS = {
        "app.api": "app.core",
        "app.plugins": "app.api",
    }
    TEST_FILE_SUFFIX = "_test.py"
    SOURCE_ROOTS = ("app/", "sdk/", "cli/")


class ArchitectureValidator:
    def __init__(self, *, project_root: Path, rules: ArchitectureRules = ArchitectureRules()) -> None:
        self.project_root = project_root
        self.rules = rules

    def validate(self) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        for source_root in self.rules.SOURCE_ROOTS:
            root = self.project_root / source_root
            if not root.exists():
                continue
            for file in root.rglob("*.py"):
                if file.name.startswith("__") or file.name.endswith(self.rules.TEST_FILE_SUFFIX):
                    continue
                violations.extend(self._validate_file(file))
        return violations

    def _validate_file(self, file: Path) -> List[RuleViolation]:
        violations: List[RuleViolation] = []
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            return [RuleViolation(str(file), exc.lineno or 0, "syntax-error", str(exc))]
        layer = self._infer_layer(file)
        if not layer:
            return []
        allowed = self.rules.LAYER_RULES.get(layer, {}).get("allowed_prefixes", ())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                if top in ("app", "sdk", "cli") and not node.module.startswith(allowed):
                    violations.append(
                        RuleViolation(
                            str(file),
                            node.lineno,
                            "layer-violation",
                            f"Module '{node.module}' imports disallowed from layer '{layer}'",
                        )
                    )
        return violations

    def _infer_layer(self, file: Path) -> Optional[str]:
        rel = file.relative_to(self.project_root).as_posix()
        for layer in self.rules.LAYER_RULES:
            if rel.startswith(layer):
                return layer
        return None
