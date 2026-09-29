import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Mapping, Optional, Pattern, Sequence, TypedDict

logger = logging.getLogger(__name__)


class LogEntry(TypedDict, total=False):
    timestamp: str
    level: str
    source: str
    message: str
    metadata: Mapping[str, Any]


@dataclass
class Pattern:
    name: str
    regex: str
    compiled: Pattern[str] = field(repr=False, init=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.regex)

    def match(self, message: str) -> Optional[Mapping[str, Any]]:
        match = self.compiled.search(message)
        if match:
            return match.groupdict()
        return None


@dataclass
class RootCause:
    code: str
    description: str
    severity: str
    affected_components: Sequence[str] = field(default_factory=list)
    matched_patterns: Sequence[str] = field(default_factory=list)
    suggested_actions: Sequence[str] = field(default_factory=list)


@dataclass
class Recommendation:
    action: str
    priority: str
    rationale: str
    estimated_effort: str
    side_effects: Sequence[str] = field(default_factory=list)


@dataclass
class AnalysisReport:
    analyzed_at: str
    log_count: int
    error_count: int
    warning_count: int
    root_causes: Sequence[RootCause] = field(default_factory=list)
    recommendations: Sequence[Recommendation] = field(default_factory=list)
    summary: str = ""
    raw_logs: Sequence[LogEntry] = field(default_factory=list)

    def to_dict(self) -> Mapping[str, Any]:
        return {
            "analyzed_at": self.analyzed_at,
            "log_count": self.log_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "root_causes": [
                {
                    "code": rc.code,
                    "description": rc.description,
                    "severity": rc.severity,
                    "affected_components": rc.affected_components,
                    "matched_patterns": rc.matched_patterns,
                    "suggested_actions": rc.suggested_actions,
                }
                for rc in self.root_causes
            ],
            "recommendations": [
                {
                    "action": rec.action,
                    "priority": rec.priority,
                        "rationale": rec.rationale,
                    "estimated_effort": rec.estimated_effort,
                    "side_effects": rec.side_effects,
                }
                for rec in self.recommendations
            ],
            "summary": self.summary,
        }


class RootCauseAnalyzer:
    def __init__(self, patterns: Sequence[Pattern]) -> None:
        self.patterns = list(patterns)

    def add_pattern(self, pattern: Pattern) -> None:
        self.patterns.append(pattern)

    def analyze(self, logs: Sequence[LogEntry]) -> AnalysisReport:
        analyzed_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        root_causes: List[RootCause] = []
        recommendations: List[Recommendation] = []
        error_count = 0
        warning_count = 0

        matched_patterns: Mapping[str, List[RootCause]] = {}

        for entry in logs:
            level = entry.get("level", "").lower()
            message = entry.get("message", "")

            if level in ("error", "critical", "fatal"):
                error_count += 1
            elif level == "warning":
                warning_count += 1

            for pattern in self.patterns:
                groupdict = pattern.match(message)
                if not groupdict:
                    continue

                matched_patterns.setdefault(pattern.name, []).append(
                    RootCause(
                        code=groupdict.get("code", "UNKNOWN"),
                        description=groupdict.get("description", message),
                        severity=groupdict.get("severity", level),
                        affected_components=groupdict.get("component", "").split(",") if groupdict.get("component") else [],
                        matched_patterns=[pattern.name],
                        suggested_actions=groupdict.get("actions", "").split(",") if groupdict.get("actions") else [],
                    )
                )

        for pattern_name, causes in matched_patterns.items():
            root_causes.append(causes[0])

        for cause in root_causes:
            for action in cause.suggested_actions:
                if action:
                    recommendations.append(
                        Recommendation(
                            action=action.strip(),
                            priority="high" if cause.severity in ("critical", "fatal") else "medium",
                            rationale=f"Matched pattern {cause.matched_patterns[0]} for {cause.code}",
                            estimated_effort="low",
                            side_effects=[],
                        )
                    )

        summary_parts = [f"{len(logs)} logs analyzed"]
        if error_count:
            summary_parts.append(f"{error_count} errors")
        if warning_count:
            summary_parts.append(f"{warning_count} warnings")
        if root_causes:
            summary_parts.append(f"{len(root_causes)} root cause(s) found")

        return AnalysisReport(
            analyzed_at=analyzed_at,
            log_count=len(logs),
            error_count=error_count,
            warning_count=warning_count,
            root_causes=root_causes,
            recommendations=recommendations,
            summary=", ".join(summary_parts) if summary_parts else "no issues found",
            raw_logs=list(logs),
        )
