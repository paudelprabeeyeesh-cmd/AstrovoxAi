import hashlib


class FullFileRewrite:
    def generate(self, original: str, rewritten: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        new_lines = rewritten.splitlines(keepends=True)
        diff_lines = []
        diff_lines.append(f"--- a/{hashlib.md5(original.encode()).hexdigest()}.txt\n")
        diff_lines.append(f"+++ b/{hashlib.md5(rewritten.encode()).hexdigest()}.txt\n")
        for orig_line, new_line in zip(orig_lines, new_lines):
            if orig_line != new_line:
                diff_lines.append(f"-{orig_line}")
                diff_lines.append(f"+{new_line}")
        if len(new_lines) > len(orig_lines):
            for extra_line in new_lines[len(orig_lines):]:
                diff_lines.append(f"+{extra_line}")
        elif len(orig_lines) > len(new_lines):
            for extra_line in orig_lines[len(new_lines):]:
                diff_lines.append(f"-{extra_line}")
        return "".join(diff_lines)

    def apply(self, original: str, diff_text: str) -> str:
        result = []
        diff_lines = diff_text.splitlines(keepends=True)
        i = 0
        while i < len(diff_lines):
            line = diff_lines[i]
            if line.startswith("---") or line.startswith("+++"):
                i += 1
                continue
            if line.startswith("-"):
                i += 1
            elif line.startswith("+"):
                result.append(line[1:])
                i += 1
            else:
                i += 1
        return "".join(result)

    def validate(self, original: str, rewritten: str) -> bool:
        return isinstance(original, str) and isinstance(rewritten, str) and len(rewritten) > 0
