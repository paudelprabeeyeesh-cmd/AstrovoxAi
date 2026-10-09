

class StructuredToolCall:
    def __init__(self, file_path: str, start: int, end: int, new_text: str):
        self.file_path = file_path
        self.start = start
        self.end = end
        self.new_text = new_text

    def validate_grammar(self) -> bool:
        if not isinstance(self.file_path, str) or not self.file_path:
            return False
        if not isinstance(self.start, int) or not isinstance(self.end, int):
            return False
        if self.start < 0 or self.end < 0:
            return False
        if self.start > self.end:
            return False
        if not isinstance(self.new_text, str):
            return False
        return True

    def apply(self, original: str) -> str:
        if not self.validate_grammar():
            raise ValueError("Invalid grammar constraints")
        lines = original.splitlines(keepends=True)
        start_idx = max(0, self.start - 1)
        end_idx = min(len(lines), self.end)
        if start_idx > len(lines) or end_idx < 0:
            raise ValueError("Range out of bounds")
        new_lines = self.new_text.splitlines(keepends=True)
        lines[start_idx:end_idx] = new_lines
        return "".join(lines)

    def diff_hunk(self, original: str) -> str:
        if not self.validate_grammar():
            raise ValueError("Invalid grammar constraints")
        lines = original.splitlines(keepends=True)
        start_idx = max(0, self.start - 1)
        end_idx = min(len(lines), self.end)
        removed = lines[start_idx:end_idx]
        new_lines = self.new_text.splitlines(keepends=True)
        added = new_lines
        result = []
        result.append(f"@@ -{self.start},{len(removed)} +{self.start},{len(added)} @@\n")
        for r in removed:
            result.append(f"-{r}")
        for a in added:
            result.append(f"+{a}")
        return "".join(result)

    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "start": self.start,
            "end": self.end,
            "new_text": self.new_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StructuredToolCall":
        return cls(data["file"], data["start"], data["end"], data["new_text"])
