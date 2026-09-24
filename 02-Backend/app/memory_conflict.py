import logging
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    memory_a: dict[str, Any]
    memory_b: dict[str, Any]
    conflict_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryConflictDetector:
    def detect_conflicts(self, memories: list[dict[str, Any]]) -> list[Conflict]:
        conflicts: list[Conflict] = []
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                a, b = memories[i], memories[j]
                if a.get("key") == b.get("key") and a.get("user_id") == b.get("user_id"):
                    if a.get("value") != b.get("value"):
                        conflicts.append(Conflict(memory_a=a, memory_b=b, conflict_type="value_mismatch"))
        return conflicts

    def resolve_conflict(self, conflict: Conflict, strategy: str) -> dict[str, Any]:
        if strategy == "newest":
            a_created = conflict.memory_a.get("created_at", "")
            b_created = conflict.memory_b.get("created_at", "")
            return conflict.memory_b if b_created >= a_created else conflict.memory_a
        if strategy == "most_important":
            a_score = conflict.memory_a.get("importance_score", 0.0)
            b_score = conflict.memory_b.get("importance_score", 0.0)
            return conflict.memory_a if a_score >= b_score else conflict.memory_b
        if strategy == "user_choice":
            return conflict.memory_b
        return conflict.memory_a

    def merge_memories(self, mem1: dict[str, Any], mem2: dict[str, Any]) -> dict[str, Any]:
        merged = dict(mem1)
        merged["value"] = f"{mem1.get('value', '')}\n---\n{mem2.get('value', '')}"
        merged["metadata"] = {**(mem1.get("metadata", {})), **(mem2.get("metadata", {}))}
        return merged
