from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence


@dataclass
class LeaderboardEntry:
    model_name: str
    benchmark: str
    score: float
    stderr: float
    timestamp: str
    rank: int = 0


@dataclass
class HistoricalResult:
    model_name: str
    benchmark: str
    score: float
    timestamp: str


class BenchmarkReporter:
    def __init__(self, results_dir: str = "benchmark_results") -> None:
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

    def generate_html_report(
        self,
        report: Dict[str, Any],
        title: str = "Benchmark Report",
        output_path: Optional[str] = None,
    ) -> str:
        model_name = report.get("model_name", "unknown")
        timestamp = report.get("timestamp", datetime.utcnow().isoformat() + "Z")
        results = report.get("results", {})

        rows = []
        for name, data in results.items():
            score = data.get("score", 0.0)
            stderr = data.get("stderr", 0.0)
            rows.append(
                f"<tr><td>{name}</td><td>{score:.4f}</td><td>{stderr:.4f}</td><td>{score - 1.96 * stderr:.4f}</td><td>{score + 1.96 * stderr:.4f}</td></tr>"
            )

        aggregate = report.get("aggregate_score")
        aggregate_row = ""
        if aggregate is not None:
            aggregate_row = f"<tr><td><strong>aggregate</strong></td><td><strong>{aggregate:.4f}</strong></td><td colspan='3'></td></tr>"

        html = f"""<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; }}
    h1 {{ color: #333; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #4CAF50; color: white; }}
    tr:nth-child(even) {{ background-color: #f2f2f2; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <p><strong>Model:</strong> {model_name}</p>
  <p><strong>Timestamp:</strong> {timestamp}</p>
  <table>
    <thead>
      <tr><th>Benchmark</th><th>Score</th><th>Std Error</th><th>95% CI Lower</th><th>95% CI Upper</th></tr>
    </thead>
    <tbody>
      {aggregate_row}
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>"""

        if output_path:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        return html

    def generate_markdown_report(
        self,
        report: Dict[str, Any],
        title: str = "Benchmark Report",
    ) -> str:
        model_name = report.get("model_name", "unknown")
        timestamp = report.get("timestamp", "")
        results = report.get("results", {})
        aggregate = report.get("aggregate_score")

        lines = [
            f"# {title}",
            "",
            f"- **Model:** {model_name}",
            f"- **Timestamp:** {timestamp}",
            "",
            "## Results",
            "",
            "| Benchmark | Score | Std Error | 95% CI Lower | 95% CI Upper |",
            "|-----------|-------|-----------|--------------|--------------|",
        ]

        for name, data in results.items():
            score = data.get("score", 0.0)
            stderr = data.get("stderr", 0.0)
            lower = score - 1.96 * stderr
            upper = score + 1.96 * stderr
            lines.append(f"| {name} | {score:.4f} | {stderr:.4f} | {lower:.4f} | {upper:.4f} |")

        if aggregate is not None:
            lines.append(f"| **aggregate** | **{aggregate:.4f}** | | | |")

        lines.append("")
        return "\n".join(lines)

    def generate_comparison_markdown(
        self,
        reports: Sequence[Dict[str, Any]],
        title: str = "Benchmark Comparison",
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"- **Generated:** {datetime.utcnow().isoformat()}Z",
            f"- **Reports compared:** {len(reports)}",
            "",
        ]

        if len(reports) < 2:
            lines.append("At least two reports are required for comparison.")
            return "\n".join(lines)

        all_benchmarks: List[str] = []
        for report in reports:
            all_benchmarks.extend(report.get("results", {}).keys())
        all_benchmarks = sorted(set(all_benchmarks))

        header = ["Benchmark"] + [r.get("model_name", f"report_{i}") for i, r in enumerate(reports)]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")

        for bench in all_benchmarks:
            row = [bench]
            for report in reports:
                data = report.get("results", {}).get(bench, {})
                score = data.get("score", "N/A")
                row.append(f"{score:.4f}" if isinstance(score, float) else str(score))
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")
        return "\n".join(lines)

    def load_report(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_historical(
        self, pattern: str = "benchmark_results/*.json"
    ) -> List[HistoricalResult]:
        import glob

        history: List[HistoricalResult] = []
        for path in glob.glob(os.path.join(self.results_dir, "*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                model_name = data.get("model_name", "unknown")
                timestamp = data.get("timestamp", "")
                for bench, res in data.get("results", {}).items():
                    history.append(
                        HistoricalResult(
                            model_name=model_name,
                            benchmark=bench,
                            score=res.get("score", 0.0),
                            timestamp=timestamp,
                        )
                    )
            except Exception:
                continue
        return history

    def build_leaderboard(
        self,
        history: Sequence[HistoricalResult],
        benchmark: str,
        top_k: int = 10,
    ) -> List[LeaderboardEntry]:
        filtered = [h for h in history if h.benchmark == benchmark]
        best: Dict[str, HistoricalResult] = {}
        for h in filtered:
            current = best.get(h.model_name)
            if current is None or h.score > current.score:
                best[h.model_name] = h
        ranked = sorted(best.values(), key=lambda h: h.score, reverse=True)[:top_k]
        return [
            LeaderboardEntry(
                model_name=r.model_name,
                benchmark=r.benchmark,
                score=r.score,
                stderr=0.0,
                timestamp=r.timestamp,
                rank=idx + 1,
            )
            for idx, r in enumerate(ranked)
        ]

    def save_leaderboard(
        self,
        leaderboard: Sequence[LeaderboardEntry],
        output_path: Optional[str] = None,
    ) -> str:
        target = output_path or os.path.join(self.results_dir, "leaderboard.json")
        data = [
            {
                "rank": entry.rank,
                "model_name": entry.model_name,
                "benchmark": entry.benchmark,
                "score": entry.score,
                "stderr": entry.stderr,
                "timestamp": entry.timestamp,
            }
            for entry in leaderboard
        ]
        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return target
