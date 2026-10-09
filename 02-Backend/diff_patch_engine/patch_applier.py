from typing import Dict, List, Optional, Tuple

from diff_patch_engine.unified_diff import UnifiedDiffGenerator
from diff_patch_engine.uniqueness_enforcement import UniquenessEnforcer


class PatchApplier:
    @staticmethod
    def apply_search_replace(
        file_content: str,
        old_text: str,
        new_text: str,
    ) -> Dict:
        enforcer = UniquenessEnforcer()
        count = enforcer.count_occurrences(file_content, old_text)
        if count == 0:
            return {
                "success": False,
                "result": file_content,
                "conflict": True,
                "conflict_reason": "old_text not found in file_content",
                "old_text_occurrences": 0,
            }
        if count > 1:
            return {
                "success": False,
                "result": file_content,
                "conflict": True,
                "conflict_reason": "old_text is not unique in file_content",
                "old_text_occurrences": count,
            }
        result = file_content.replace(old_text, new_text, 1)
        return {
            "success": True,
            "result": result,
            "conflict": False,
            "conflict_reason": "",
            "old_text_occurrences": count,
        }

    @staticmethod
    def apply_unified_hunks(
        original: str,
        hunks: List[Tuple],
    ) -> Dict:
        enforcer = UniquenessEnforcer()
        for hunk in hunks:
            if not hunk:
                continue
            removed = hunk[4] if len(hunk) > 4 else ""
            count = enforcer.count_occurrences(original, removed)
            if count > 1:
                return {
                    "success": False,
                    "result": original,
                    "conflict": True,
                    "conflict_reason": (
                        "removed text in hunk is not unique in original"
                    ),
                }
        result = UnifiedDiffGenerator.apply(original, hunks)
        return {
            "success": True,
            "result": result,
            "conflict": False,
            "conflict_reason": "",
        }

    @staticmethod
    def apply_diff_text(original: str, diff_text: str) -> Dict:
        hunks = UnifiedDiffGenerator.parse(diff_text)
        return PatchApplier.apply_unified_hunks(original, hunks)

    @staticmethod
    def apply_patch(file_content: str, patch: Dict) -> Dict:
        patch_type = patch.get("type", "search_replace")
        if patch_type == "search_replace":
            old_text = patch.get("old_text", "")
            new_text = patch.get("new_text", "")
            return PatchApplier.apply_search_replace(file_content, old_text, new_text)
        if patch_type == "unified":
            hunks = patch.get("hunks", [])
            return PatchApplier.apply_unified_hunks(file_content, hunks)
        return {
            "success": False,
            "result": file_content,
            "conflict": True,
            "conflict_reason": f"unsupported patch type: {patch_type}",
        }

    @staticmethod
    def batch_apply(file_content: str, patches: List[Dict]) -> Dict:
        results = []
        current = file_content
        for patch in patches:
            result = PatchApplier.apply_patch(current, patch)
            results.append(result)
            current = result.get("result", current)
        all_conflicts = [r for r in results if r.get("conflict")]
        return {
            "success": len(all_conflicts) == 0,
            "result": current,
            "conflicts": all_conflicts,
            "applied": results,
        }
