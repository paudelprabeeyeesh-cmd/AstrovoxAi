"""Security report generation in multiple formats."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Sequence


@dataclass
class Finding:
    title: str
    severity: str
    description: str
    recommendation: str


@dataclass
class ReportSection:
    title: str
    content: str
    findings: list[Finding] = field(default_factory=list)


@dataclass
class ReportMetadata:
    title: str
    author: str
    created_at: float
    version: str


@dataclass
class SecurityReport:
    metadata: ReportMetadata
    sections: list[ReportSection]
    findings: list[Finding]


class ReportGenerator:
    def __init__(self, metadata: ReportMetadata) -> None:
        self.metadata = metadata
        self.sections: list[ReportSection] = []
        self.findings: list[Finding] = []

    def add_section(self, title: str, content: str) -> None:
        self.sections.append(ReportSection(title=title, content=content))

    def add_finding(self, title: str, severity: str, description: str, recommendation: str) -> None:
        finding = Finding(title=title, severity=severity, description=description, recommendation=recommendation)
        self.findings.append(finding)
        if self.sections:
            self.sections[-1].findings.append(finding)

    def add_executive_summary(self, text: str) -> None:
        self.sections.insert(0, ReportSection(title="Executive Summary", content=text))

    def to_text(self) -> str:
        lines = [f"# {self.metadata.title}", f"Author: {self.metadata.author}", f"Version: {self.metadata.version}", ""]
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append(section.content)
            if section.findings:
                for f in section.findings:
                    lines.append(f"- [{f.severity.upper()}] {f.title}: {f.description}")
                    lines.append(f"  Recommendation: {f.recommendation}")
            lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        data = {
            "metadata": {
                "title": self.metadata.title,
                "author": self.metadata.author,
                "created_at": self.metadata.created_at,
                "version": self.metadata.version,
            },
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "findings": [
                        {"title": f.title, "severity": f.severity, "description": f.description, "recommendation": f.recommendation}
                        for f in s.findings
                    ],
                }
                for s in self.sections
            ],
            "findings": [
                {"title": f.title, "severity": f.severity, "description": f.description, "recommendation": f.recommendation}
                for f in self.findings
            ],
        }
        return json.dumps(data, indent=2)

    def to_html(self) -> str:
        lines = [f"<html><head><title>{self.metadata.title}</title></head><body>", f"<h1>{self.metadata.title}</h1>", f"<p>Author: {self.metadata.author}</p>"]
        for section in self.sections:
            lines.append(f"<h2>{section.title}</h2>")
            lines.append(f"<p>{section.content}</p>")
            if section.findings:
                lines.append("<ul>")
                for f in section.findings:
                    lines.append(f"<li><strong>[{f.severity.upper()}]</strong> {f.title}: {f.description}<br/>Recommendation: {f.recommendation}</li>")
                lines.append("</ul>")
        lines.append("</body></html>")
        return "\n".join(lines)

    def get_findings_by_severity(self, severity: str) -> list[Finding]:
        return [f for f in self.findings if f.severity == severity]
