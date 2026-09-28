from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from models.llm.tracking.experiment import Experiment
from models.llm.tracking.metrics import MetricStore


class ReportGenerator:
    def __init__(self, experiment: Experiment) -> None:
        self.experiment = experiment

    def generate_html(self, output_path: str) -> None:
        run_ids = list(self.experiment.runs.keys())
        runs_data = self.experiment.compare_runs(run_ids)
        metric_keys = sorted({k for r in self.experiment.runs.values() for k in r.metrics})

        experiment_options = "".join(f"<option value='{name}'>{name}</option>" for name in self.experiment.runs)
        experiments_json = json.dumps(list(self.experiment.runs.keys()))

        chart_sections = ""
        for key in metric_keys:
            datasets = []
            for run_id, run in self.experiment.runs.items():
                if key not in run.metrics:
                    continue
                scalar_pts = [(i, v) for i, (ts, v) in enumerate(run.metrics[key]) if not isinstance(ts, str)]
                if scalar_pts:
                    datasets.append(json.dumps({"label": run_id[:8], "data": [{"x": i, "y": v} for i, v in scalar_pts], "borderWidth": 1}))
            datasets_str = ",".join(datasets)
            chart_sections += f"""
    <div class=\"card\">
      <h3>{key}</h3>
      <canvas id=\"chart-{key}\" class=\"chart\"></canvas>
    </div>
    <script>
      const ctx_{key} = document.getElementById('chart-{key}').getContext('2d');
      new Chart(ctx_{key}, {{type: 'line', data: {{datasets: [{datasets_str}]}}, options: {{scales: {{x: {{type: 'linear', title: {{display: true, text: 'Step'}}}}, y: {{title: {{display: true, text: '{key}'}}}}}}}}}});
    </script>\n"""

        param_keys = sorted({k for r in self.experiment.runs.values() for k in r.parameters})
        param_headers = "".join(f"<th>{p}</th>" for p in param_keys)
        param_rows = ""
        for run_id, data in runs_data.items():
            param_values = "".join(f"<td>{data.get('parameters', {}).get(p, 'N/A')}</td>" for p in param_keys)
            param_rows += f"        <tr><td>{run_id[:8]}</td>{param_values}</tr>\n"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Experiment Report: {self.experiment.name}</title>
    <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .card {{ background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        canvas {{ max-height: 250px; }}
    </style>
</head>
<body>
    <h1>Experiment Report: {self.experiment.name}</h1>
    <p>Generated at: {datetime.now(timezone.utc).isoformat()}</p>

    <div class=\"card\">
      <h2>Runs Overview</h2>
      <table>
        <tr><th>Run ID</th><th>State</th><th>Duration (s)</th><th>Parameters</th></tr>
"""
        for run_id, data in runs_data.items():
            params = ", ".join(f"{k}={v}" for k, v in data.get("parameters", {}).items())
            duration = data.get("duration_seconds", "N/A")
            html += f"        <tr><td>{run_id[:8]}</td><td>{data['state']}</td><td>{duration}</td><td>{params}</td></tr>\n"

        html += "      </table>\n    </div>\n"

        html += chart_sections

        html += f"""    <div class=\"card\">
      <h2>Hyperparameter Comparison</h2>
      <table>
        <tr><th>Run ID</th>{param_headers}</tr>
        {param_rows}
      </table>
    </div>
</body>
</html>"""

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    def compare_runs(self, run_ids: list[str], output_path: str) -> None:
        comparison = self.experiment.compare_runs(run_ids)
        lines = [f"# Run Comparison\n"]
        for run_id, data in comparison.items():
            lines.append(f"## {run_id[:8]}")
            lines.append(f"- State: {data['state']}")
            lines.append(f"- Duration: {data.get('duration_seconds', 'N/A')}s")
            for k, v in data.get("metrics", {}).items():
                lines.append(f"- {k}: {v}")
            lines.append("")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
