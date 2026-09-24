import ast
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CoverageEntry:
    test_name: str
    file_path: str
    covered_lines: List[int]
    score: float = 0.0


@dataclass
class ChangedFile:
    path: str
    added_lines: List[int]
    removed_lines: List[int]
    modified_lines: List[int]


class TargetedTestSelector:
    def __init__(self, coverage_map: Optional[Dict[str, List[int]]] = None):
        self.coverage_map = coverage_map or {}

    def record_coverage(self, test_name: str, file_path: str, covered_lines: List[int]) -> None:
        self.coverage_map[file_path] = list(set(self.coverage_map.get(file_path, []) + covered_lines))

    def select(
        self,
        changed_files: List[ChangedFile],
        all_tests: List[str],
    ) -> List[CoverageEntry]:
        candidates: Dict[str, CoverageEntry] = {}
        for test in all_tests:
            covered = set()
            for file_path, lines in self.coverage_map.items():
                if any(c.path == file_path for c in changed_files):
                    covered.update(lines)
            score = 0.0
            for changed in changed_files:
                if not changed.added_lines and not changed.modified_lines:
                    continue
                relevant = covered.intersection(set(changed.added_lines + changed.modified_lines))
                denom = max(len(changed.added_lines + changed.modified_lines), 1)
                score = max(score, len(relevant) / denom)
            candidates[test] = CoverageEntry(
                test_name=test,
                file_path=",".join(c.path for c in changed_files),
                covered_lines=list(covered),
                score=score,
            )
        selected = [e for e in candidates.values() if e.score > 0.0]
        selected.sort(key=lambda e: e.score, reverse=True)
        return selected

    def selection_coverage(
        self,
        selected: List[CoverageEntry],
        changed_files: List[ChangedFile],
    ) -> Dict[str, float]:
        if not changed_files:
            return {"overall": 0.0, "by_file": {}}
        all_changed = set()
        for c in changed_files:
            all_changed.update(c.added_lines + c.modified_lines)
        covered = set()
        for entry in selected:
            covered.update(entry.covered_lines)
        overall = len(covered.intersection(all_changed)) / max(len(all_changed), 1)
        by_file = {}
        for changed in changed_files:
            relevant = set(changed.added_lines + changed.modified_lines)
            by_file[changed.path] = len(covered.intersection(relevant)) / max(len(relevant), 1)
        return {"overall": round(overall, 4), "by_file": {k: round(v, 4) for k, v in by_file.items()}}
