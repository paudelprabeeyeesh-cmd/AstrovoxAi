"""Coding agent orchestrator."""

from __future__ import annotations

import logging
from typing import Any

from backend.app.coding.indexer import Indexer
from backend.app.coding.parser import TreeSitterParser
from backend.app.coding.lsp import LSPService
from backend.app.coding.project_graph import ProjectGraphService
from backend.app.coding.multi_file_editor import MultiFileEditor
from backend.app.coding.dependency_analyzer import DependencyAnalyzer
from ASTROVOX_AI.ai_core.coding.planner import TaskPlanner
from ASTROVOX_AI.ai_core.coding.executor import CodeExecutor
from ASTROVOX_AI.ai_core.coding.architect import AIArchitect
from ASTROVOX_AI.ai_core.coding.refactorer import AIRefactorer
from ASTROVOX_AI.ai_core.coding.reviewer import AIReviewer
from ASTROVOX_AI.ai_core.coding.tester import AITester
from ASTROVOX_AI.ai_core.coding.api_gen import AIAPIGenerator
from ASTROVOX_AI.ai_core.coding.docs_gen import AIDocGenerator

logger = logging.getLogger(__name__)


class CodingAgent:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path
        self.indexer = Indexer(repo_path)
        self.parser = TreeSitterParser()
        self.lsp = LSPService(repo_path)
        self.graph = ProjectGraphService(repo_path)
        self.editor = MultiFileEditor(repo_path)
        self.deps = DependencyAnalyzer(repo_path)
        self.planner = TaskPlanner()
        self.executor = CodeExecutor(repo_path)
        self.architect = AIArchitect(repo_path)
        self.refactorer = AIRefactorer(repo_path)
        self.reviewer = AIReviewer(repo_path)
        self.tester = AITester(repo_path)
        self.api_gen = AIAPIGenerator(repo_path)
        self.docs_gen = AIDocGenerator(repo_path)

    def handle(self, request: str) -> dict[str, Any]:
        plan = self.planner.plan(request)
        task_type = plan.get("task_type", "general")
        steps = plan.get("steps", [])
        results = []
        for step in steps:
            action = step.get("action")
            if action == "index":
                results.append({"step": action, "result": self.indexer.build()})
            elif action == "analyze":
                idx = self.indexer.index
                results.append({"step": action, "result": self.deps.analyze(idx)})
            elif action == "refactor":
                target = self._pick_target()
                if target:
                    results.append({"step": action, "result": self.refactorer.suggest(target)})
            elif action == "verify":
                results.append({"step": action, "result": self.executor.lint()})
            elif action == "generate_tests":
                target = self._pick_target()
                if target:
                    results.append({"step": action, "result": self.tester.generate(target, "sample_symbol")})
            elif action == "run_tests":
                results.append({"step": action, "result": self.executor.run_tests()})
            elif action == "scan_bugs":
                target = self._pick_target()
                if target:
                    results.append({"step": action, "result": self.reviewer.review(target)})
            elif action == "review":
                target = self._pick_target()
                if target:
                    results.append({"step": action, "result": self.reviewer.review(target)})
            elif action == "summarize":
                results.append({"step": action, "result": {"summary": "review complete"}})
            elif action == "generate_docs":
                target = self._pick_target()
                if target:
                    results.append({"step": action, "result": self.docs_gen.generate(target)})
            elif action == "extract_routes":
                results.append({"step": action, "result": self.api_gen.generate_spec([])})
            elif action == "infer_openapi":
                results.append({"step": action, "result": self.api_gen.generate_spec([])})
            elif action == "generate_client":
                results.append({"step": action, "result": self.api_gen.generate_client({}, "python")})
            elif action == "build_graph":
                idx = self.indexer.index
                results.append({"step": action, "result": self.graph.build(idx)})
            elif action == "analyze_arch":
                idx = self.indexer.index
                deps = self.deps.analyze(idx)
                summary = idx.to_dict()
                results.append({"step": action, "result": self.architect.analyze(summary, deps)})
            else:
                results.append({"step": action, "result": {"status": "handled"}})
        return {"task_type": task_type, "steps": steps, "results": results}

    def _pick_target(self) -> str | None:
        for rel in self.indexer.index.files:
            if rel.endswith(".py"):
                return rel
        return None
