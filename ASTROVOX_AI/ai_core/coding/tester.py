"""AI-enhanced test generator."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class AITester:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def generate(self, file_path: str, symbol_name: str) -> dict[str, Any]:
        full_path = os.path.join(self.repo_path, file_path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            return {"file": file_path, "error": str(exc)}
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".py":
            return self._python_test(file_path, symbol_name, content)
        if ext in {".js", ".ts", ".jsx", ".tsx"}:
            return self._js_test(file_path, symbol_name, content)
        return {"file": file_path, "error": f"unsupported language: {ext}"}

    def _python_test(self, file_path: str, symbol_name: str, content: str) -> dict[str, Any]:
        module = file_path.replace(os.sep, ".").replace("/", ".").rstrip(".py")
        test_name = f"test_{symbol_name}"
        return {
            "file": file_path,
            "test_file": f"test_{os.path.basename(file_path)}",
            "content": f"import pytest\nfrom {module} import {symbol_name}\n\n\ndef {test_name}():\n    result = {symbol_name}()\n    assert result is not None\n",
        }

    def _js_test(self, file_path: str, symbol_name: str, content: str) -> dict[str, Any]:
        return {
            "file": file_path,
            "test_file": f"{os.path.basename(file_path)}.test.ts",
            "content": f"describe('{symbol_name}', () => {{\n  it('should execute', () => {{\n    expect({symbol_name}()).toBeDefined();\n  }});\n}});\n",
        }
