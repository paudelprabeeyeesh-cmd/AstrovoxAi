from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


@dataclass
class FeatureAblationResult:
    feature: str
    score_with: float
    score_without: float
    impact: float
    p_value: Optional[float] = None


@dataclass
class AblationReport:
    experiment_id: str
    results: List[FeatureAblationResult]
    summary: Dict
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class StatisticalTester:
    @staticmethod
    def paired_t_test(a: torch.Tensor, b: torch.Tensor) -> Tuple[float, float]:
        diff = a - b
        mean_diff = diff.mean()
        std_diff = diff.std(unbiased=True)
        n = diff.numel()
        if std_diff == 0:
            return 0.0, 1.0
        se = std_diff / (n ** 0.5)
        if se == 0:
            return 0.0, 1.0
        t_stat = mean_diff / se
        p_value = 2.0 * (1.0 - torch.distributions.Normal(0.0, 1.0).cdf(torch.abs(torch.tensor(t_stat))))
        return t_stat, p_value.item()

    @staticmethod
    def wilcoxon_test(a: torch.Tensor, b: torch.Tensor) -> float:
        diff = a - b
        ranks = torch.argsort(torch.abs(diff), dim=0)
        pos_ranks = ranks[diff > 0]
        W = pos_ranks.sum().item() if pos_ranks.numel() > 0 else 0
        return W


class AblationStudy:
    def __init__(self, model: nn.Module, feature_extractor):
        self.model = model
        self.feature_extractor = feature_extractor

    def ablate_feature(self, x: torch.Tensor, feature_name: str, enabled: bool) -> torch.Tensor:
        return self.feature_extractor(x, **{feature_name: enabled})

    def compare(self, x: torch.Tensor, y: torch.Tensor, feature_name: str, enabled: bool) -> FeatureAblationResult:
        with torch.no_grad():
            score_with = torch.nn.functional.cross_entropy(self.model(x), y).item()
            score_without = torch.nn.functional.cross_entropy(self.model(x), y).item()
        impact = score_without - score_with
        return FeatureAblationResult(feature=feature_name, score_with=score_with, score_without=score_without, impact=impact)

    def run_feature_ablation(self, x: torch.Tensor, y: torch.Tensor, features: List[str]) -> List[FeatureAblationResult]:
        results: List[FeatureAblationResult] = []
        for feature in features:
            result = self.compare(x, y, feature, enabled=True)
            results.append(result)
            logger.info("Feature ablation %s: impact=%.4f", feature, result.impact)
        return results

    def generate_report(self, experiment_id: str, results: List[FeatureAblationResult]) -> AblationReport:
        impacts = [r.impact for r in results]
        positive = sum(1 for i in impacts if i > 0)
        negative = sum(1 for i in impacts if i < 0)
        neutral = len(impacts) - positive - negative
        summary = {
            "total_features": len(results),
            "positive_impact": positive,
            "negative_impact": negative,
            "neutral_impact": neutral,
            "mean_impact": sum(impacts) / len(impacts) if impacts else 0,
        }
        return AblationReport(experiment_id=experiment_id, results=results, summary=summary)


class ReportGenerator:
    @staticmethod
    def to_markdown(report: AblationReport) -> str:
        lines = [
            f"# Ablation Study: {report.experiment_id}",
            f"Generated: {report.generated_at}",
            "",
            "## Summary",
            f"Total features: {report.summary.get('total_features', 0)}",
            f"Positive impact: {report.summary.get('positive_impact', 0)}",
            f"Negative impact: {report.summary.get('negative_impact', 0)}",
            f"Neutral impact: {report.summary.get('neutral_impact', 0)}",
            "",
            "## Feature Results",
            "",
        ]
        for r in report.results:
            lines.append(f"### {r.feature}")
            lines.append(f"- Score with: {r.score_with:.4f}")
            lines.append(f"- Score without: {r.score_without:.4f}")
            lines.append(f"- Impact: {r.impact:.4f}")
            if r.p_value is not None:
                lines.append(f"- P-value: {r.p_value:.4e}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def to_pdf(report: AblationReport, output_path: str) -> str:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            doc = SimpleDocTemplate(output_path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = [Paragraph(f"Ablation Study: {report.experiment_id}", styles["Title"])]
            data = [["Feature", "Score With", "Score Without", "Impact"]]
            for r in report.results:
                data.append([r.feature, f"{r.score_with:.4f}", f"{r.score_without:.4f}", f"{r.impact:.4f}"])
            table = Table(data)
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.grey), ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, 0), 14), ("BOTTOMPADDING", (0, 0), (-1, 0), 12), ("BACKGROUND", (0, 1), (-1, -1), colors.beige), ("GRID", (0, 0), (-1, -1), 1, colors.black)]))
            elements.append(table)
            doc.build(elements)
            return output_path
        except ImportError:
            logger.warning("reportlab not installed, falling back to markdown")
            return ""
