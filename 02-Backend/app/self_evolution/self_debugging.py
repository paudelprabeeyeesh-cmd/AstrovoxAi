import ast
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class BugReport:
    bug_id: str
    module: str
    error: str
    traceback: str
    diagnosis: str = ""
    fixability: float = 0.0
    patches: list[dict[str, Any]] = field(default_factory=list)
    status: str = "open"
    created_at: float = field(default_factory=time.time)


@dataclass
class RepairPatch:
    patch_id: str
    bug_id: str
    description: str
    patch: str
    confidence: float = 0.0
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)


class SelfDebuggingService:
    def __init__(self) -> None:
        self._bugs: dict[str, BugReport] = {}
        self._patches: dict[str, RepairPatch] = {}
        self._module_registry: dict[str, str] = {}
        self._client = None
        self._max_traceback_len = 4096

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register_module(self, module_name: str, source: str) -> None:
        self._module_registry[module_name] = source

    def report_bug(self, module: str, error: str, traceback: str) -> str:
        bug_id = f"bug_{uuid.uuid4().hex[:8]}"
        truncated = traceback[: self._max_traceback_len]
        bug = BugReport(bug_id=bug_id, module=module, error=error, traceback=truncated)
        self._bugs[bug_id] = bug
        logger.info("Reported bug %s in %s: %s", bug_id, module, error)
        return bug_id

    def diagnose(self, bug_id: str) -> dict[str, Any]:
        bug = self._bugs.get(bug_id)
        if not bug:
            return {"bug_id": bug_id, "status": "not_found"}

        diagnosis = self._llm_diagnose(bug)
        fixability = self._estimate_fixability(bug, diagnosis)
        bug.diagnosis = diagnosis
        bug.fixability = fixability
        logger.info("Diagnosed bug %s: fixability=%.2f", bug_id, fixability)
        return {
            "bug_id": bug_id,
            "module": bug.module,
            "error": bug.error,
            "diagnosis": diagnosis,
            "fixability": round(fixability, 4),
            "status": "diagnosed",
        }

    def repair(self, bug_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        bug = self._bugs.get(bug_id)
        if not bug:
            return {"status": "not_found", "bug_id": bug_id}
        if bug.status == "fixed":
            return {"status": "already_fixed", "bug_id": bug_id}

        patch_str = patch.get("patch", "")
        description = patch.get("description", "auto_patch")
        confidence = float(patch.get("confidence", 0.0))
        patch_id = f"patch_{uuid.uuid4().hex[:8]}"
        repair_patch = RepairPatch(patch_id=patch_id, bug_id=bug_id, description=description, patch=patch_str, confidence=confidence)
        self._patches[patch_id] = repair_patch
        bug.patches.append(patch.toDict() if hasattr(patch, "toDict") else patch)

        if confidence >= 0.7:
            bug.status = "fixed"
            repair_patch.status = "applied"
            if bug.module in self._module_registry and patch_str:
                self._module_registry[bug.module] = patch_str
            logger.info("Repaired bug %s with patch %s", bug_id, patch_id)
        else:
            bug.status = "patched"
            repair_patch.status = "review_required"

        return {
            "status": repair_patch.status,
            "bug_id": bug_id,
            "patch_id": patch_id,
            "confidence": round(confidence, 4),
        }

    def get_bug(self, bug_id: str) -> dict[str, Any] | None:
        bug = self._bugs.get(bug_id)
        if not bug:
            return None
        return {
            "bug_id": bug.bug_id,
            "module": bug.module,
            "error": bug.error,
            "traceback": bug.traceback,
            "diagnosis": bug.diagnosis,
            "fixability": bug.fixability,
            "status": bug.status,
            "patch_count": len(bug.patches),
            "created_at": bug.created_at,
        }

    def list_bugs(self, module: str | None = None, status: str | None = None) -> list[str]:
        bugs = list(self._bugs.values())
        if module:
            bugs = [b for b in bugs if b.module == module]
        if status:
            bugs = [b for b in bugs if b.status == status]
        return [b.bug_id for b in bugs]

    def propose_repair(self, bug_id: str) -> dict[str, Any]:
        bug = self._bugs.get(bug_id)
        if not bug:
            return {"bug_id": bug_id, "status": "not_found"}
        if not bug.diagnosis:
            self.diagnose(bug_id)
            bug = self._bugs.get(bug_id)

        source = self._module_registry.get(bug.module, "")
        try:
            prompt = (
                "Given the module source, bug diagnosis, and error, propose a minimal repair patch. "
                "Return JSON with keys: patch (string), confidence (float 0-1), description (string).\n"
                f"Module source:\n{source}\nDiagnosis: {bug.diagnosis}\nError: {bug.error}\nTraceback:\n{bug.traceback}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            import json
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            patch = {"patch": data.get("patch", ""), "confidence": float(data.get("confidence", 0.0)), "description": data.get("description", "")}
            return self.repair(bug_id, patch)
        except Exception as exc:
            logger.error("Repair proposal failed: %s", exc)
            return {"bug_id": bug_id, "status": "error", "error": str(exc)}

    def _llm_diagnose(self, bug: BugReport) -> str:
        try:
            prompt = (
                "Diagnose the root cause of the bug given the module, error message, and traceback. Return a concise diagnosis string.\n"
                f"Module: {bug.module}\nError: {bug.error}\nTraceback:\n{bug.traceback}"
            )
            client = self._get_client()
            response = client.chat.completions.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content or "Unknown"
        except Exception as exc:
            logger.error("Diagnosis failed: %s", exc)
            return f"Diagnosis failed: {exc}"

    def _estimate_fixability(self, bug: BugReport, diagnosis: str) -> float:
        source = self._module_registry.get(bug.module, "")
        has_source = bool(source.strip())
        known_patterns = ["null", "undefined", "type", "import", "syntax"]
        matched = any(p in bug.error.lower() for p in known_patterns)
        score = 0.3
        if has_source:
            score += 0.3
        if matched:
            score += 0.2
        if diagnosis and diagnosis != "Unknown":
            score += 0.2
        return min(1.0, score)
