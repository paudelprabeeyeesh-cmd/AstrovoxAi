import ast
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SafetyConstraint:
    max_lines: int = 5000
    allowed_imports: list[str] = field(default_factory=lambda: ["logging", "typing", "dataclasses"])
    blocked_constructs: list[str] = field(default_factory=lambda: ["exec", "eval", "__import__", "compile"])
    requires_review: bool = True


class SelfModifyingCode:
    def __init__(self, safety: SafetyConstraint | None = None):
        self.safety = safety or SafetyConstraint()
        self.code_registry: dict[str, str] = {}
        self.modifications: list[dict[str, Any]] = []

    def register(self, name: str, source: str) -> None:
        self.code_registry[name] = source

    def propose_patch(self, name: str, new_source: str) -> dict[str, Any]:
        if name not in self.code_registry:
            return {"error": "module not found"}
        check = self._safety_check(new_source)
        if not check["safe"]:
            return {"status": "rejected", "reasons": check["reasons"]}
        return {"status": "approved", "patch": new_source}

    def apply_patch(self, name: str, new_source: str) -> dict[str, Any]:
        proposal = self.propose_patch(name, new_source)
        if proposal.get("status") == "approved":
            self.code_registry[name] = new_source
            self.modifications.append({"module": name, "applied": True})
            return {"status": "applied", "module": name}
        return proposal

    def _safety_check(self, source: str) -> dict[str, Any]:
        reasons = []
        if len(source.splitlines()) > self.safety.max_lines:
            reasons.append("exceeds max_lines")
        for construct in self.safety.blocked_constructs:
            if construct in source:
                reasons.append(f"blocked construct: {construct}")
        try:
            ast.parse(source)
        except SyntaxError as e:
            reasons.append(f"syntax_error: {e}")
        return {"safe": len(reasons) == 0, "reasons": reasons}
