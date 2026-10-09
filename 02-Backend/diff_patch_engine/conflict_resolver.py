from typing import List, Optional


class ConflictResolver:
    class Conflict:
        def __init__(self, kind: str, description: str, source: str = ""):
            self.kind = kind
            self.description = description
            self.source = source

    @staticmethod
    def detect_conflicts(
        source_patch: Dict,
        destination_patch: Dict,
        original: str,
    ) -> List["ConflictResolver.Conflict"]:
        conflicts: List[ConflictResolver.Conflict] = []
        for patch in [source_patch, destination_patch]:
            patch_type = patch.get("type", "search_replace")
            if patch_type == "search_replace":
                old_text = patch.get("old_text", "")
                enforcer = ConflictResolver._count_in(original, old_text)
                if enforcer > 1:
                    conflicts.append(
                        ConflictResolver.Conflict(
                            kind="non_unique",
                            description=(
                                "old_text is not unique in original"
                            ),
                            source=patch.get("type", ""),
                        )
                    )
        return conflicts

    @staticmethod
    def resolve_conflicts(
        original: str,
        source_patch: Dict,
        destination_patch: Dict,
        strategy: str = "source",
    ) -> Dict:
        conflicts = ConflictResolver.detect_conflicts(
            source_patch, destination_patch, original
        )
        if conflicts and strategy not in ("source", "destination", "skip"):
            raise ValueError(f"unsupported conflict strategy: {strategy}")
        if strategy == "skip":
            return {
                "result": original,
                "strategy": "skip",
                "conflicts": conflicts,
            }
        if strategy == "source":
            applied = ConflictResolver._apply_safe(original, source_patch)
            return {
                "result": applied.get("result", original),
                "strategy": "source",
                "conflicts": conflicts,
            }
        applied = ConflictResolver._apply_safe(original, destination_patch)
        return {
            "result": applied.get("result", original),
            "strategy": "destination",
            "conflicts": conflicts,
        }

    @staticmethod
    def merge_hunks(source_hunks: List[Tuple], destination_hunks: List[Tuple]) -> List[Tuple]:
        merged = list(source_hunks)
        seen_indices = set()
        for hunk in destination_hunks:
            if not hunk:
                continue
            start = hunk[0] if len(hunk) > 0 else 0
            key = (hunk, start)
            if key not in seen_indices:
                merged.append(hunk)
                seen_indices.add(key)
        return merged

    @staticmethod
    def generate_conflict_marker(
        original: str,
        source_patch: Dict,
        destination_patch: Dict,
    ) -> str:
        marker = "<<<<<<< source\n"
        source_applied = ConflictResolver._apply_safe(original, source_patch)
        marker += source_applied.get("result", original)
        marker += "\n=======\n"
        dest_applied = ConflictResolver._apply_safe(original, destination_patch)
        marker += dest_applied.get("result", original)
        marker += "\n>>>>>>> destination\n"
        return marker

    @staticmethod
    def _apply_safe(file_content: str, patch: Dict) -> Dict:
        from diff_patch_engine.patch_applier import PatchApplier
        return PatchApplier.apply_patch(file_content, patch)

    @staticmethod
    def _count_in(text: str, pattern: str) -> int:
        return text.count(pattern)
