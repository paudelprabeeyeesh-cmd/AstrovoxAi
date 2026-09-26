"""Main coding agent orchestrator with task routing."""

from __future__ import annotations

import logging
import os
from typing import Any

from .architecture import ArchitectureAdvisor
from .bugfix import BugFixer
from .dependencies import DependencyAnalyzer
from .docs import DocGenerator
from .indexer import RepositoryIndex
from .lsp import LSPClient
from .multi_edit import MultiFileEdit
from .project_graph import ProjectGraph
from .refactor import RefactorEngine
from .review import CodeReviewer
from .tests import TestGenerator
from .api_gen import APIGenerator

logger = logging.getLogger(__name__)


class CodingAgent:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)
        self.index = RepositoryIndex(repo_path)
        self.graph = ProjectGraph(repo_path)
        self.lsp_cache: dict[str, LSPClient] = {}
        self.indexer = self.index
        self.parser = None
        self.lsp = None
        self.project_graph = self.graph
        self.multi_edit = MultiFileEdit(repo_path)
        self.dependencies = DependencyAnalyzer(repo_path)
        self.refactor = RefactorEngine(repo_path)
        self.tests = TestGenerator(repo_path)
        self.bugfix = BugFixer(repo_path)
        self.review = CodeReviewer(repo_path)
        self.docs = DocGenerator(repo_path)
        self.api_gen = APIGenerator(repo_path)
        self.architecture = ArchitectureAdvisor(repo_path)

    def build_index(self) -> dict[str, Any]:
        return self.index.build()

    def build_graph(self) -> dict[str, Any]:
        self.index.build()
        return self.graph.build(self.index)

    def get_lsp(self, language: str) -> LSPClient:
        if language not in self.lsp_cache:
            client = LSPClient(language, self.repo_path)
            client.start()
            self.lsp_cache[language] = client
        return self.lsp_cache[language]

    def go_to_definition(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        language = self._detect_language(file_path)
        client = self.get_lsp(language)
        return client.definition(file_path, line, character)

    def find_references(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        language = self._detect_language(file_path)
        client = self.get_lsp(language)
        return client.references(file_path, line, character)

    def hover(self, file_path: str, line: int, character: int) -> dict[str, Any]:
        language = self._detect_language(file_path)
        client = self.get_lsp(language)
        return client.hover(file_path, line, character)

    def rename_symbol(self, file_path: str, line: int, character: int, new_name: str) -> dict[str, Any]:
        language = self._detect_language(file_path)
        client = self.get_lsp(language)
        return client.rename(file_path, line, character, new_name)

    def analyze_dependencies(self) -> dict[str, Any]:
        self.index.build()
        return self.dependencies.analyze_repo(self.index)

    def suggest_refactors(self, file_path: str) -> dict[str, Any]:
        return self.refactor.suggest_refactors(file_path)

    def generate_tests(self, file_path: str, symbol_name: str) -> dict[str, Any]:
        return self.tests.generate_for_function(file_path, symbol_name)

    def generate_class_tests(self, file_path: str, class_name: str) -> dict[str, Any]:
        return self.tests.generate_for_class(file_path, class_name)

    def scan_bugs(self, file_path: str) -> dict[str, Any]:
        return self.bugfix.scan_file(file_path)

    def scan_repo_bugs(self) -> dict[str, Any]:
        self.index.build()
        return self.bugfix.scan_repo(self.index)

    def review_file(self, file_path: str) -> dict[str, Any]:
        return self.review.review_file(file_path)

    def review_diff(self, diff_text: str) -> dict[str, Any]:
        return self.review.review_diff(diff_text)

    def generate_docs(self, file_path: str) -> dict[str, Any]:
        return self.docs.generate_for_file(file_path)

    def generate_project_docs(self) -> dict[str, Any]:
        self.index.build()
        return self.docs.generate_for_project(self.index)

    def infer_api(self, file_paths: list[str]) -> dict[str, Any]:
        return self.api_gen.infer_openapi(file_paths)

    def generate_api_client(self, spec: dict[str, Any], language: str) -> dict[str, Any]:
        return self.api_gen.generate_client(spec, language)

    def architecture_analysis(self) -> dict[str, Any]:
        self.index.build()
        self.graph.build(self.index)
        return self.architecture.analyze(self.graph, self.dependencies)

    def suggest_architecture_layers(self, files: list[str]) -> dict[str, Any]:
        return self.architecture.suggest_layers(files)

    def execute_task(self, task: str, target: str | None = None) -> dict[str, Any]:
        task_lower = task.lower()
        if "index" in task_lower or "indexing" in task_lower:
            return {"task": task, "result": self.build_index()}
        if "graph" in task_lower or "understand" in task_lower:
            return {"task": task, "result": self.build_graph()}
        if "dependency" in task_lower or "dependencies" in task_lower:
            return {"task": task, "result": self.analyze_dependencies()}
        if "refactor" in task_lower:
            if not target:
                return {"task": task, "error": "target file required for refactoring"}
            return {"task": task, "result": self.suggest_refactors(target)}
        if "test" in task_lower:
            if not target:
                return {"task": task, "error": "target file required for test generation"}
            return {"task": task, "result": self.generate_tests(target, "")}
        if "bug" in task_lower or "fix" in task_lower:
            if target:
                return {"task": task, "result": self.scan_bugs(target)}
            return {"task": task, "result": self.scan_repo_bugs()}
        if "review" in task_lower:
            if target:
                return {"task": task, "result": self.review_file(target)}
            return {"task": task, "error": "target file required for review"}
        if "doc" in task_lower or "documentation" in task_lower:
            if target:
                return {"task": task, "result": self.generate_docs(target)}
            return {"task": task, "result": self.generate_project_docs()}
        if "api" in task_lower or "openapi" in task_lower:
            return {"task": task, "result": self.infer_api([target] if target else [])}
        if "architecture" in task_lower:
            return {"task": task, "result": self.architecture_analysis()}
        if "lsp" in task_lower or "definition" in task_lower or "reference" in task_lower:
            if not target:
                return {"task": task, "error": "target file required for LSP"}
            return {"task": task, "result": self.go_to_definition(target, 0, 0)}
        return {"task": task, "error": "unknown task", "supported": ["index", "graph", "dependency", "refactor", "test", "bug", "review", "doc", "api", "architecture", "lsp"]}

    def _detect_language(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mapping = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
        }
        return mapping.get(ext, "python")

    def shutdown(self) -> None:
        for client in self.lsp_cache.values():
            try:
                client.shutdown()
            except Exception:
                pass
