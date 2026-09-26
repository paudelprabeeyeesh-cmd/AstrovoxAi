"""Documentation generator for the AstrovoxAI platform."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional


class DocsGenerator:
    def __init__(self, docs_root: Path, output_dir: Path) -> None:
        self.docs_root = docs_root
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_api_reference(self) -> Path:
        api_docs = self.docs_root / "api-reference.md"
        if not api_docs.exists():
            return self.output_dir / "api-reference.md"
        out = self.output_dir / "api-reference.md"
        out.write_text(api_docs.read_text(encoding="utf-8"), encoding="utf-8")
        return out

    def generate_sdk_docs(self) -> Path:
        out = self.output_dir / "sdk.md"
        lines = ["# SDK Documentation\n\n", "## Available SDKs\n\n"]
        for lang in ["python", "typescript", "go", "java", "rust", "csharp"]:
            lines.append(f"- [{lang.title()}](../sdk/{lang}/README.md)\n")
        out.write_text("".join(lines), encoding="utf-8")
        return out

    def generate_tutorials_index(self) -> Path:
        out = self.output_dir / "tutorials.md"
        tutorials_dir = self.docs_root / "tutorials"
        lines = ["# Tutorials\n\n"]
        if tutorials_dir.exists():
            for f in sorted(tutorials_dir.glob("*.md")):
                lines.append(f"- [{f.stem}](tutorials/{f.name})\n")
        out.write_text("".join(lines), encoding="utf-8")
        return out

    def generate_runbooks_index(self) -> Path:
        out = self.output_dir / "runbooks.md"
        runbooks_dir = self.docs_root / "runbooks"
        lines = ["# Runbooks\n\n", "| Runbook | Description |\n", "|---------|-------------|\n"]
        if runbooks_dir.exists():
            for f in sorted(runbooks_dir.glob("*.md")):
                title = f.stem.replace("-", " ").title()
                lines.append(f"| [{title}](runbooks/{f.name}) | {title} |\n")
        out.write_text("".join(lines), encoding="utf-8")
        return out

    def generate_all(self) -> Dict[str, Path]:
        return {
            "api": self.generate_api_reference(),
            "sdk": self.generate_sdk_docs(),
            "tutorials": self.generate_tutorials_index(),
            "runbooks": self.generate_runbooks_index(),
        }
