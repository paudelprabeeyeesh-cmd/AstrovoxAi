"""Diff engine and conflict resolver for collaborative editing."""
from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    operation: str
    content: str
    line_start: int = 0


@dataclass
class Conflict:
    hunk_index: int
    base: str
    ours: str
    theirs: str


class DiffEngine:
    @staticmethod
    def diff(old_text: str, new_text: str) -> List[DiffHunk]:
        differ = difflib.SequenceMatcher(None, old_text.splitlines(), new_text.splitlines())
        hunks: List[DiffHunk] = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == "replace":
                hunks.append(DiffHunk(operation="replace", content="\n".join(new_text.splitlines()[j1:j2])))
            elif tag == "delete":
                hunks.append(DiffHunk(operation="delete", content="\n".join(old_text.splitlines()[i1:i2])))
            elif tag == "insert":
                hunks.append(DiffHunk(operation="insert", content="\n".join(new_text.splitlines()[j1:j2])))
        return hunks

    @staticmethod
    def apply(base: str, hunks: List[DiffHunk]) -> str:
        lines = base.splitlines()
        offset = 0
        for hunk in hunks:
            if hunk.operation == "insert":
                lines.insert(offset, hunk.content)
                offset += 1
            elif hunk.operation == "delete":
                del lines[offset:offset + max(1, hunk.content.count("\n") + 1)]
            elif hunk.operation == "replace":
                del lines[offset:offset + max(1, hunk.content.count("\n") + 1)]
                lines.insert(offset, hunk.content)
                offset += 1
        return "\n".join(lines)


class ConflictResolver:
    @staticmethod
    def three_way(base: str, ours: str, theirs: str) -> str:
        base_lines = base.splitlines()
        ours_lines = ours.splitlines()
        theirs_lines = theirs.splitlines()
        merged = []
        i = 0
        while i < len(base_lines):
            ours_idx = i if i < len(ours_lines) else -1
            theirs_idx = i if i < len(theirs_lines) else -1
            ours_val = ours_lines[ours_idx] if ours_idx >= 0 else ""
            theirs_val = theirs_lines[theirs_idx] if theirs_idx >= 0 else ""
            base_val = base_lines[i]
            if ours_val == base_val:
                merged.append(theirs_val)
            elif theirs_val == base_val:
                merged.append(ours_val)
            elif ours_val == theirs_val:
                merged.append(ours_val)
            else:
                merged.append(f"<<<<<<< ours\n{ours_val}\n=======\n{theirs_val}\n>>>>>>> theirs")
            i += 1
        return "\n".join(merged)

    @staticmethod
    def find_conflicts(base: str, ours: str, theirs: str) -> List[Conflict]:
        conflicts: List[Conflict] = []
        differ = difflib.SequenceMatcher(None, base.splitlines(), ours.splitlines())
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag == "replace":
                base_segment = "\n".join(base.splitlines()[i1:i2])
                ours_segment = "\n".join(ours.splitlines()[j1:j2])
                their_differ = difflib.SequenceMatcher(None, base_segment.splitlines(), theirs.splitlines())
                for t, ti1, ti2, tj1, tj2 in their_differ.get_opcodes():
                    if t == "replace":
                        conflicts.append(Conflict(
                            hunk_index=len(conflicts),
                            base=base_segment,
                            ours=ours_segment,
                            theirs="\n".join(theirs.splitlines()[tj1:tj2]),
                        ))
        return conflicts


diff_engine = DiffEngine()
conflict_resolver = ConflictResolver()
