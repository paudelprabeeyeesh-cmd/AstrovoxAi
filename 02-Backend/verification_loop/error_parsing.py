import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional



@dataclass
class ErrorRecord:
    tool: str
    file_path: str
    line: int
    column: int
    severity: str
    message: str
    rule: Optional[str] = None
    raw: str = ""


@dataclass
class ParseResult:
    tool: str
    errors: List[ErrorRecord] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class ErrorParser:
    PATTERNS = {
        "tsc": re.compile(r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\):\s*(?P<severity>error|warning)\s+(?P<rule>\w+):\s*(?P<message>.+?)(?:\s*\[(?P<rule_override>[^\]]+)\])?$"),
        "mypy": re.compile(r"^(?P<file>.+?):(?P<line>\d+):\s*(?P<severity>error|warning):\s*(?P<message>.+?)(?:\s*\[(?P<rule>[^\]]+)\])?$"),
        "rustc": re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<severity>error|warning)\[(?P<rule>[^\]]+)\]:\s*(?P<message>.+)$"),
        "eslint": re.compile(r"^(?P<file>.+?):line\s+(?P<line>\d+),\s*col\s+(?P<column>\d+),\s*(?P<severity>Error|Warning),\s*(?P<rule>[^-\s][^-\s]+(?:\-[^-\s]+)*)\s*-\s*(?P<message>.+)$"),
    }

    def parse(self, tool: str, output: str) -> ParseResult:
        pattern = self.PATTERNS.get(tool)
        if not pattern:
            raise ValueError(f"Unsupported tool: {tool}")
        errors = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = pattern.match(line)
            if not match:
                continue
            gd = match.groupdict()
            rule = gd.get("rule") or gd.get("rule_override")
            errors.append(ErrorRecord(
                tool=tool,
                file_path=gd.get("file", ""),
                line=int(gd.get("line", 0)),
                column=int(gd.get("column", gd.get("col", 0))),
                severity=gd.get("severity", "unknown"),
                message=gd.get("message", "").strip(),
                rule=rule,
                raw=line,
            ))
        by_severity: Dict[str, int] = {}
        for e in errors:
            by_severity[e.severity] = by_severity.get(e.severity, 0) + 1
        by_file: Dict[str, int] = {}
        for e in errors:
            by_file[e.file_path] = by_file.get(e.file_path, 0) + 1
        return ParseResult(
            tool=tool,
            errors=errors,
            summary={
                "total_errors": len(errors),
                "by_severity": by_severity,
                "by_file": by_file,
                "error_rate": round(len(errors) / max(len(output.splitlines()), 1), 4),
            },
        )

    def structured_errors(self, tool: str, output: str) -> List[Dict[str, Any]]:
        result = self.parse(tool, output)
        return [
            {
                "tool": e.tool,
                "file": e.file_path,
                "line": e.line,
                "column": e.column,
                "severity": e.severity,
                "message": e.message,
                "rule": e.rule,
                "raw": e.raw,
            }
            for e in result.errors
        ]
