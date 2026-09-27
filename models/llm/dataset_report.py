"""
Dataset Report Generator

Generates a comprehensive markdown report from dataset validation results,
including statistics, distributions, sample texts, and ASCII/markdown charts.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report data structure
# ---------------------------------------------------------------------------

@dataclass
class ReportConfig:
    title: str = "Dataset Validation Report"
    output_path: str = "dataset_report.md"
    max_sample_texts: int = 5
    max_chart_rows: int = 10
    include_samples: bool = True
    include_charts: bool = True


@dataclass
class DatasetReport:
    stats: Any
    config: ReportConfig = field(default_factory=ReportConfig)

    def _ascii_bar(self, label: str, value: int, total: int, width: int = 30) -> str:
        if total == 0:
            pct = 0.0
            bar = ""
        else:
            pct = value / total
            bar = "#" * int(pct * width)
        return f"{label:<20} |{bar:<{width}} | {value} ({pct:.1%})"

    def _ascii_chart(self, distribution: Dict[str, int], title: str) -> str:
        if not distribution:
            return f"## {title}\nNo data available.\n"
        total = sum(distribution.values())
        lines = [f"## {title}"]
        lines.append("```")
        for label, value in distribution.items():
            lines.append(self._ascii_bar(label, value, total))
        lines.append("```")
        return "\n".join(lines)

    def _markdown_table(self, distribution: Dict[str, int], title: str) -> str:
        if not distribution:
            return f"## {title}\nNo data available.\n"
        total = sum(distribution.values())
        lines = [f"## {title}", "", "| Label | Count | Percentage |", "|-------|-------|------------|"]
        for label, value in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total * 100) if total > 0 else 0.0
            lines.append(f"| {label} | {value} | {pct:.2f}% |")
        lines.append("")
        return "\n".join(lines)

    def _format_number(self, value: Union[int, float]) -> str:
        if isinstance(value, int):
            return f"{value:,}"
        return f"{value:,.2f}"

    def generate(self) -> str:
        stats = self.stats
        lines: List[str] = []
        lines.append(f"# {self.config.title}")
        lines.append("")
        lines.append(f"*Generated on: {self._timestamp()}*")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Documents:** {self._format_number(stats.total_documents)}")
        lines.append(f"- **Valid Documents:** {self._format_number(stats.valid_documents)}")
        lines.append(f"- **Total Tokens:** {self._format_number(stats.total_tokens)}")
        lines.append(f"- **Avg Tokens per Doc:** {self._format_number(stats.avg_document_length)}")
        lines.append(f"- **Vocab Coverage:** {stats.vocab_coverage:.2f}%")
        lines.append(f"- **Vocab Size:** {self._format_number(stats.vocab_size)}")
        lines.append("")

        lines.append("## Removal Statistics")
        lines.append("")
        lines.append("| Filter | Removed Count |")
        lines.append("|--------|---------------|")
        lines.append(f"| Corrupted Samples | {self._format_number(stats.removed_corrupted)} |")
        lines.append(f"| HTML Only | {self._format_number(stats.removed_html_only)} |")
        lines.append(f"| Exact Duplicates | {self._format_number(stats.removed_exact_duplicates)} |")
        lines.append(f"| Near Duplicates | {self._format_number(stats.removed_near_duplicates)} |")
        lines.append(f"| Low Quality | {self._format_number(stats.removed_low_quality)} |")
        lines.append("")

        if self.config.include_charts:
            lines.append("## Distributions")
            lines.append("")
            if stats.language_distribution:
                lines.append(self._markdown_table(stats.language_distribution, "Language Distribution"))
            if stats.domain_distribution:
                lines.append(self._markdown_table(stats.domain_distribution, "Domain Distribution"))
            if stats.length_distribution:
                lines.append(self._ascii_chart(stats.length_distribution, "Document Length Distribution (words)"))
            lines.append("")

        if self.config.include_samples and stats.sample_texts:
            lines.append("## Sample Texts")
            lines.append("")
            for i, sample in enumerate(stats.sample_texts[: self.config.max_sample_texts], 1):
                lines.append(f"### Sample {i}")
                lines.append("")
                lines.append("```text")
                lines.append(sample[:1000])
                lines.append("```")
                lines.append("")

        return "\n".join(lines)

    def _timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save(self, path: Optional[str] = None) -> str:
        output = path or self.config.output_path
        try:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(self.generate())
            logger.info("Report saved to %s", output)
            return output
        except OSError as exc:
            logger.error("Failed to save report: %s", exc)
            raise


def generate_report(
    stats: Any,
    output_path: str = "dataset_report.md",
    title: str = "Dataset Validation Report",
    max_sample_texts: int = 5,
) -> str:
    config = ReportConfig(
        title=title,
        output_path=output_path,
        max_sample_texts=max_sample_texts,
    )
    report = DatasetReport(stats=stats, config=config)
    return report.save(output_path)
