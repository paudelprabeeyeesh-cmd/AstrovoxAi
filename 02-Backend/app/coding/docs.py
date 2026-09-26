"""Documentation generation from source code."""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class DocGenerator:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def generate_for_file(self, file_path: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc), "docs": ""}
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            return self._generate_python_docs(content, file_path)
        return self._generate_generic_docs(content, file_path)

    def generate_for_project(self, index: Any) -> dict[str, Any]:
        modules: list[dict[str, Any]] = []
        for rel_path, file_info in index.files.items():
            result = self.generate_for_file(rel_path)
            modules.append({"file": rel_path, "docs": result.get("docs", "")})
        readme = self._generate_readme(index, modules)
        return {"modules": modules, "readme": readme}

    def _generate_python_docs(self, content: str, file_path: str) -> dict[str, Any]:
        try:
            import ast

            tree = ast.parse(content)
        except SyntaxError as exc:
            return {"file": file_path, "error": str(exc), "docs": ""}
        docs: list[str] = [f"# {os.path.basename(file_path)}\n"]
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                args = [a.arg for a in node.args.args] if hasattr(node, "args") else []
                returns = ast.unparse(node.returns) if hasattr(node, "returns") and node.returns else "None"
                doc = ast.get_docstring(node)
                docs.append(f"## {name}\n")
                if doc:
                    docs.append(f"{doc}\n")
                docs.append(f"**Signature:** `{name}({', '.join(args)}) -> {returns}`\n")
        return {"file": file_path, "docs": "\n".join(docs)}

    def _generate_generic_docs(self, content: str, file_path: str) -> dict[str, Any]:
        lines = content.splitlines()
        docs = [f"# {os.path.basename(file_path)}\n"]
        symbols: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("class ") or stripped.startswith("function ") or stripped.startswith("def "):
                symbols.append(stripped)
        docs.append("## Symbols\n")
        for sym in symbols:
            docs.append(f"- `{sym}`\n")
        return {"file": file_path, "docs": "\n".join(docs)}

    def _generate_readme(self, index: Any, modules: list[dict[str, Any]]) -> str:
        lines = ["# Project Documentation\n", "## Modules\n"]
        for m in modules:
            lines.append(f"- `{m['file']}`\n")
        return "\n".join(lines)
