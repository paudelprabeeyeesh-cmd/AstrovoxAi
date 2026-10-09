import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReportSection:
    title: str
    content: Dict[str, Any]


@dataclass
class VerificationReport:
    title: str
    generated_at: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    def __init__(self, title: str = "Verification Report"):
        self.title = title

    def build(self, sections: List[ReportSection], metadata: Optional[Dict[str, Any]] = None) -> VerificationReport:
        return VerificationReport(
            title=self.title,
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            sections=sections,
            metadata=metadata or {},
        )

    def to_text(self, report: VerificationReport) -> str:
        lines = [f"# {report.title}", f"Generated: {report.generated_at}", ""]
        for section in report.sections:
            lines.append(f"## {section.title}")
            for key, value in section.content.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        if report.metadata:
            lines.append("## Metadata")
            for key, value in report.metadata.items():
                lines.append(f"- {key}: {value}")
            lines.append("")
        return "\n".join(lines)

    def to_markdown(self, report: VerificationReport) -> str:
        return self.to_text(report)

    def aggregate(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = len(results)
        passed = sum(1 for r in results if r.get("passed", False))
        failed = total - passed
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / max(total, 1), 4),
        }
