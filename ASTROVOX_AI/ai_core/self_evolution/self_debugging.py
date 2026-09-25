import ast
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BugReport:
    module: str
    error: str
    traceback: str
    severity: str = "medium"


@dataclass
class RepairPatch:
    module: str
    patch: str
    confidence: float = 0.0
    verified: bool = False


class SelfDebuggingRepair:
    def __init__(self):
        self.bugs: list[BugReport] = []
        self.patches: list[RepairPatch] = []
        self.repair_history: list[dict[str, Any]] = []

    def report_bug(self, bug: BugReport) -> str:
        self.bugs.append(bug)
        bug_id = f"{bug.module}:{len(self.bugs)}"
        return bug_id

    def diagnose(self, bug_id: str) -> dict[str, Any]:
        for b in self.bugs:
            if f"{b.module}:{self.bugs.index(b)+1}" == bug_id:
                return {"bug_id": bug_id, "diagnosis": b.error, "fixability": 0.5}
        return {"error": "bug not found"}

    def repair(self, bug_id: str, patch: RepairPatch) -> dict[str, Any]:
        self.patches.append(patch)
        return {"status": "patch_recorded", "bug_id": bug_id, "patch_confidence": patch.confidence}
