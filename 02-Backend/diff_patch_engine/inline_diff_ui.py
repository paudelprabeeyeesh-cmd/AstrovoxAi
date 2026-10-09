from typing import List, Dict
from dataclasses import dataclass


@dataclass
class DiffLine:
    line_number: int
    content: str
    type: str


@dataclass
class DecorationRange:
    start_line: int
    start_character: int
    end_line: int
    end_character: int
    color: str
    type: str


class InlineDiffUI:
    def __init__(self):
        self.diff_lines: List[DiffLine] = []
        self.stream_buffer: str = ""

    def stream_diff(self, chunk: str) -> None:
        self.stream_buffer += chunk
        while "\n" in self.stream_buffer:
            line, self.stream_buffer = self.stream_buffer.split("\n", 1)
            self._process_line(line)

    def _process_line(self, line: str) -> None:
        if line.startswith("+"):
            self.diff_lines.append(DiffLine(len(self.diff_lines) + 1, line[1:], "added"))
        elif line.startswith("-"):
            self.diff_lines.append(DiffLine(len(self.diff_lines) + 1, line[1:], "removed"))
        elif line.startswith("@@"):
            self.diff_lines.append(DiffLine(len(self.diff_lines) + 1, line, "header"))
        else:
            self.diff_lines.append(DiffLine(len(self.diff_lines) + 1, line, "context"))

    def flush(self) -> None:
        if self.stream_buffer:
            self._process_line(self.stream_buffer)
            self.stream_buffer = ""

    def generate_decorations(self) -> List[Dict]:
        current_line = 1
        result = []
        for diff_line in self.diff_lines:
            if diff_line.type == "added":
                result.append(
                    {
                        "range": {
                            "start": {"line": current_line - 1, "character": 0},
                            "end": {
                                "line": current_line - 1,
                                "character": len(diff_line.content),
                            },
                        },
                        "options": {
                            "backgroundColor": "#e6ffed",
                            "color": "#22863a",
                            "isWholeLine": True,
                        },
                    }
                )
            elif diff_line.type == "removed":
                result.append(
                    {
                        "range": {
                            "start": {"line": current_line - 1, "character": 0},
                            "end": {
                                "line": current_line - 1,
                                "character": len(diff_line.content),
                            },
                        },
                        "options": {
                            "backgroundColor": "#ffeef0",
                            "color": "#b31d28",
                            "isWholeLine": True,
                        },
                    }
                )
            current_line += 1
        return result

    def get_diff_lines(self) -> List[Dict]:
        return [
            {"line": dl.line_number, "content": dl.content, "type": dl.type}
            for dl in self.diff_lines
        ]
