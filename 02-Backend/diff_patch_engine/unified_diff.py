from typing import List, Tuple


class UnifiedDiffGenerator:
    @staticmethod
    def generate(original: str, rewritten: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        new_lines = rewritten.splitlines(keepends=True)
        diff_lines = []
        diff_lines.append("--- original\n")
        diff_lines.append("+++ rewritten\n")
        i = 0
        while i < len(orig_lines) or i < len(new_lines):
            orig_line = orig_lines[i] if i < len(orig_lines) else ""
            new_line = new_lines[i] if i < len(new_lines) else ""
            if orig_line != new_line:
                start_orig = i + 1
                start_new = i + 1
                orig_block = []
                new_block = []
                while (
                    i < len(orig_lines)
                    and i < len(new_lines)
                    and orig_lines[i] != new_lines[i]
                ):
                    orig_block.append(orig_lines[i])
                    new_block.append(new_lines[i])
                    i += 1
                while i < len(orig_lines) and orig_lines[i] not in new_lines:
                    orig_block.append(orig_lines[i])
                    i += 1
                while i < len(new_lines) and new_lines[i] not in orig_lines:
                    new_block.append(new_lines[i])
                    i += 1
                orig_count = len(orig_block)
                new_count = len(new_block)
                diff_lines.append(
                    f"@@ -{start_orig},{orig_count} +{start_new},{new_count} @@\n"
                )
                for ol in orig_block:
                    diff_lines.append(f"-{ol}")
                for nl in new_block:
                    diff_lines.append(f"+{nl}")
            else:
                i += 1
        return "".join(diff_lines)

    @staticmethod
    def parse(diff_text: str) -> List[Tuple[int, int, int, int, str, str]]:
        hunks = []
        lines = diff_text.splitlines(keepends=True)
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith("@@"):
                parts = line.split()
                for part in parts:
                    if part.startswith("-"):
                        range_str = part[1:]
                        range_parts = range_str.split(",")
                        start_orig = int(range_parts[0])
                        count_orig = int(range_parts[1]) if len(range_parts) > 1 else 1
                    elif part.startswith("+"):
                        range_str = part[1:]
                        range_parts = range_str.split(",")
                        start_new = int(range_parts[0])
                        count_new = int(range_parts[1]) if len(range_parts) > 1 else 1
                i += 1
                removed = []
                added = []
                while i < len(lines) and not lines[i].startswith("@@"):
                    if lines[i].startswith("-"):
                        removed.append(lines[i][1:])
                    elif lines[i].startswith("+"):
                        added.append(lines[i][1:])
                    i += 1
                hunks.append(
                    (start_orig, count_orig, start_new, count_new, "".join(removed), "".join(added))
                )
            else:
                i += 1
        return hunks

    @staticmethod
    def apply(original: str, hunks: List[Tuple]) -> str:
        lines = original.splitlines(keepends=True)
        offset = 0
        for start_orig, count_orig, start_new, count_new, removed, added in hunks:
            idx = start_orig - 1 + offset
            if 0 <= idx <= len(lines):
                lines[idx : idx + count_orig] = [added] if added else []
                offset += len(added.splitlines(keepends=True)) - count_orig
        return "".join(lines)
