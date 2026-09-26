import ast
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Patch:
    patch_id: str
    module_name: str
    old_source: str
    new_source: str
    rationale: str
    safety_score: float = 0.0
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)


class SelfModifyingCodeService:
    def __init__(self) -> None:
        self._patches: dict[str, Patch] = {}
        self._module_registry: dict[str, str] = {}
        self._max_patch_bytes = 8192
        self._forbidden_imports = {"os", "subprocess", "sys", "shutil", "socket", "ctypes", "eval", "exec"}
        self._forbidden_attributes = {"__builtins__"}
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def register_module(self, module_name: str, source: str) -> None:
        self._module_registry[module_name] = source

    def propose_patch(self, name: str, new_source: str, rationale: str = "") -> dict[str, Any]:
        if name not in self._module_registry:
            return {"status": "not_found", "module": name}

        safety = self._compute_safety_score(new_source)
        patch_id = str(uuid.uuid4())
        patch = Patch(
            patch_id=patch_id,
            module_name=name,
            old_source=self._module_registry[name],
            new_source=new_source,
            rationale=rationale,
            safety_score=safety,
            status="proposed" if safety >= 0.7 else "rejected",
        )
        self._patches[patch_id] = patch
        logger.info("Patch %s proposed for %s (safety=%.2f)", patch_id, name, safety)
        return {
            "status": patch.status,
            "patch_id": patch_id,
            "module": name,
            "safety_score": round(safety, 4),
        }

    def apply_patch(self, name: str, new_source: str, rationale: str = "") -> dict[str, Any]:
        if name not in self._module_registry:
            return {"status": "not_found", "module": name}

        safety = self._compute_safety_score(new_source)
        if safety < 0.7:
            return {"status": "rejected", "module": name, "reason": "safety_score_below_threshold", "safety_score": round(safety, 4)}

        if not self._validate_ast(new_source):
            return {"status": "rejected", "module": name, "reason": "invalid_ast"}

        patch_id = str(uuid.uuid4())
        old = self._module_registry[name]
        patch = Patch(
            patch_id=patch_id,
            module_name=name,
            old_source=old,
            new_source=new_source,
            rationale=rationale,
            safety_score=safety,
            status="applied",
        )
        self._patches[patch_id] = patch
        self._module_registry[name] = new_source
        logger.info("Patch %s applied to %s", patch_id, name)
        return {"status": "applied", "patch_id": patch_id, "module": name, "safety_score": round(safety, 4)}

    def rollback(self, patch_id: str) -> dict[str, Any]:
        patch = self._patches.get(patch_id)
        if not patch:
            return {"status": "not_found", "patch_id": patch_id}
        if patch.status != "applied":
            return {"status": "invalid", "patch_id": patch_id, "reason": "patch_not_applied"}

        self._module_registry[patch.module_name] = patch.old_source
        patch.status = "rolled_back"
        logger.info("Rolled back patch %s for %s", patch_id, patch.module_name)
        return {"status": "rolled_back", "patch_id": patch_id, "module": patch.module_name}

    def get_patch(self, patch_id: str) -> dict[str, Any] | None:
        patch = self._patches.get(patch_id)
        if not patch:
            return None
        return {
            "patch_id": patch.patch_id,
            "module_name": patch.module_name,
            "status": patch.status,
            "safety_score": patch.safety_score,
            "rationale": patch.rationale,
            "created_at": patch.created_at,
        }

    def list_patches(self, module_name: str | None = None) -> list[dict[str, Any]]:
        patches = list(self._patches.values())
        if module_name:
            patches = [p for p in patches if p.module_name == module_name]
        return [self.get_patch(p.patch_id) for p in patches if self.get_patch(p.patch_id)]

    def get_current_source(self, module_name: str) -> str | None:
        return self._module_registry.get(module_name)

    def generate_patch_from_feedback(self, module_name: str, feedback: str) -> dict[str, Any]:
        if module_name not in self._module_registry:
            return {"status": "not_found", "module": module_name}
        current = self._module_registry[module_name]
        try:
            prompt = (
                "Given the current module source and feedback, propose a minimal patch. Return JSON with keys: new_source (string), rationale (string).\n"
                f"Current source:\n{current}\nFeedback: {feedback}"
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
            new_source = data.get("new_source", current)
            rationale = data.get("rationale", feedback)
            return self.propose_patch(module_name, new_source, rationale)
        except Exception as exc:
            logger.error("Patch generation failed: %s", exc)
            return {"status": "error", "module": module_name, "error": str(exc)}

    def _compute_safety_score(self, source: str) -> float:
        if not source or not source.strip():
            return 0.0
        score = 0.5
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self._forbidden_imports:
                            return 0.0
                if isinstance(node, ast.ImportFrom):
                    if node.module in self._forbidden_imports:
                        return 0.0
            score = 0.8
            if len(source.encode("utf-8")) <= self._max_patch_bytes:
                score += 0.2
        except SyntaxError:
            score = 0.0
        return min(score, 1.0)

    def _validate_ast(self, source: str) -> bool:
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in self._forbidden_attributes:
                    return False
            return True
        except SyntaxError:
            return False
