from __future__ import annotations

import json
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from models.llm.tracking.experiment import Experiment


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>AstrovoxAi Experiment Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .card {{ background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }}
        canvas {{ max-height: 250px; }}
    </style>
</head>
<body>
    <h1>AstrovoxAi Experiment Dashboard</h1>
    <div class="card">
        <h2>Experiments</h2>
        <select id="experiment-select" onchange="loadRuns()">
            <option value="">Select experiment</option>
            {experiment_options}
        </select>
        <select id="run-select" multiple size="5" style="width:100%;margin-top:8px;"></select>
    </div>
    <div class="grid" id="charts"></div>
    <script>
        const experiments = {experiments_json};
        function loadRuns() {{
            const exp = document.getElementById('experiment-select').value;
            const runSelect = document.getElementById('run-select');
            runSelect.innerHTML = '';
            if (!exp || !experiments[exp]) return;
            experiments[exp].forEach(run => {{
                const opt = document.createElement('option');
                opt.value = run; opt.textContent = run.slice(0,8);
                runSelect.appendChild(opt);
            }});
            loadCharts();
        }}
        function loadCharts() {{
            const exp = document.getElementById('experiment-select').value;
            const runSelect = document.getElementById('run-select');
            const selected = Array.from(runSelect.selectedOptions).map(o => o.value);
            const chartsDiv = document.getElementById('charts');
            chartsDiv.innerHTML = '';
            if (!exp || selected.length === 0) return;
            fetch('/api/experiments/' + encodeURIComponent(exp) + '/metrics?run_ids=' + encodeURIComponent(selected.join(',')))
                .then(r => r.json())
                .then(data => {{
                    Object.entries(data.metrics || {{}}).forEach(([key, series]) => {{
                        const card = document.createElement('div'); card.className = 'card';
                        const canvas = document.createElement('canvas');
                        card.innerHTML = '<h3>' + key + '</h3>';
                        card.appendChild(canvas);
                        chartsDiv.appendChild(card);
                        const datasets = series.map(s => ({{label: s.run_id.slice(0,8), data: s.values, borderWidth: 1}}));
                        new Chart(canvas, {{type: 'line', data: {{datasets}}, options: {{scales: {{x: {{type: 'linear', title: {{display: true, text: 'Step'}}}}, y: {{title: {{display: true, text: key}}}}}}}}}});
                    }});
                }});
        }}
        document.getElementById('run-select').addEventListener('change', loadCharts);
    </script>
</body>
</html>"""


class Dashboard:
    def __init__(self, experiment: Experiment) -> None:
        self.experiment = experiment
        self.app = FastAPI(title="AstrovoxAi Tracking Dashboard")
        self._setup_routes()

    def _setup_routes(self) -> None:
        app = self.app

        @app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            experiment_options = "".join(f"<option value='{name}'>{name}</option>" for name in self.experiment.runs)
            experiments_json = json.dumps(list(self.experiment.runs.keys()))
            return HTMLResponse(DASHBOARD_HTML.format(experiment_options=experiment_options, experiments_json=experiments_json))

        @app.get("/api/experiments/{experiment_name}/runs")
        async def list_runs(experiment_name: str):
            runs = {rid: {"state": r.state, "parameters": r.parameters} for rid, r in self.experiment.runs.items()}
            return JSONResponse({"experiment": experiment_name, "runs": runs})

        @app.get("/api/experiments/{experiment_name}/metrics")
        async def get_metrics(experiment_name: str, run_ids: str = ""):
            ids = run_ids.split(",") if run_ids else list(self.experiment.runs.keys())
            metrics_data: dict[str, Any] = {}
            from models.llm.tracking.metrics import MetricStore
            store = MetricStore(self.experiment.storage_dir)
            for run_id in ids:
                run = self.experiment.runs.get(run_id)
                if not run:
                    continue
                for key, points in run.metrics.items():
                    scalar_pts = [(i, v) for i, (ts, v) in enumerate(points) if not isinstance(ts, str)]
                    if not scalar_pts:
                        continue
                    if key not in metrics_data:
                        metrics_data[key] = []
                    metrics_data[key].append({"run_id": run_id, "values": [{"x": i, "y": v} for i, v in scalar_pts]})
            return JSONResponse({"experiment": experiment_name, "metrics": metrics_data})

        @app.get("/api/experiments/{experiment_name}/gpu")
        async def gpu_utilization(experiment_name: str):
            return JSONResponse({"experiment": experiment_name, "gpu_utilization": []})
