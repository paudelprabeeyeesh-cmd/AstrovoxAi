"""Architecture suggestions and structural health analysis."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_ARCH_PATTERNS = [
    {
        "name": "circular_dependency",
        "check": lambda g: len(g.get("circular_dependencies", [])) > 0,
        "message": "Circular dependencies detected. Consider extracting shared interfaces or applying dependency inversion.",
        "severity": "high",
    },
    {
        "name": "large_module",
        "check": lambda g: any(f.get("size", 0) > 50000 for f in g.get("files", {}).values()),
        "message": "Module exceeds 50KB. Consider splitting into smaller modules.",
        "severity": "medium",
    },
    {
        "name": "missing_tests",
        "check": lambda g: not any("test" in f for f in g.get("files", {})),
        "message": "No test files detected. Add unit and integration tests.",
        "severity": "medium",
    },
    {
        "name": "deep_package_nesting",
        "check": lambda g: max((len(f.split("/")) for f in g.get("files", {})), default=0) > 5,
        "message": "Deep package nesting detected. Consider flattening directory structure.",
        "severity": "low",
    },
]


class ArchitectureAdvisor:
    def __init__(self, repo_path: str) -> None:
        self.repo_path = os.path.abspath(repo_path)

    def analyze(self, graph: Any, deps: Any) -> dict[str, Any]:
        summary = graph.get_architecture_summary() if hasattr(graph, "get_architecture_summary") else {}
        dep_summary = deps.analyze_repo(graph.files) if hasattr(deps, "analyze_repo") else {}
        suggestions = []
        for pattern in _ARCH_PATTERNS:
            try:
                if pattern["check"](dep_summary if isinstance(dep_summary, dict) else summary):
                    suggestions.append({"pattern": pattern["name"], "message": pattern["message"], "severity": pattern["severity"]})
            except Exception:
                continue
        return {
            "summary": summary,
            "dependency_analysis": dep_summary,
            "suggestions": suggestions,
            "health_score": max(0, 100 - len(suggestions) * 10),
        }

    def suggest_layers(self, files: list[str]) -> dict[str, Any]:
        layers = {"controllers": [], "services": [], "models": [], "utils": [], "config": []}
        for f in files:
            name = os.path.basename(f).lower()
            if "controller" in name or "route" in name or "router" in name:
                layers["controllers"].append(f)
            elif "service" in name or "engine" in name or "manager" in name:
                layers["services"].append(f)
            elif "model" in name or "schema" in name or "entity" in name:
                layers["models"].append(f)
            elif "util" in name or "helper" in name:
                layers["utils"].append(f)
            elif "config" in name or "setting" in name:
                layers["config"].append(f)
        return {"suggested_layers": layers, "message": "Consider organizing code into these layers for better maintainability."}

    def detect_anti_patterns(self, content: str, language: str = "python") -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("global "):
                issues.append({"line": i, "message": "Global state mutation detected.", "severity": "medium"})
            if "import *" in line:
                issues.append({"line": i, "message": "Wildcard import pollutes namespace.", "severity": "medium"})
            if line.strip().startswith("class ") and i < len(lines):
                if "pass" in lines[i].strip() and len(lines[i].strip()) < 10:
                    issues.append({"line": i, "message": "Empty class body; consider removing or implementing.", "severity": "low"})
        return issues
