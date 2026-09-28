import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.tracking.experiment import Experiment, Run
from models.llm.tracking.metrics import MetricStore, MetricRecord
from models.llm.tracking.reports import ReportGenerator


@pytest.fixture
def tmp_storage(tmp_path):
    return str(tmp_path / "experiments")


class TestRun:
    def test_run_defaults(self):
        run = Run(run_id="run-1", experiment_name="test")
        assert run.state == "running"
        assert run.parameters == {}
        assert run.metrics == {}
        assert run.artifacts == []
        assert run.tags == {}
        assert run.start_time is not None
        assert run.end_time is None

    def test_run_initialization(self):
        run = Run(run_id="run-1", experiment_name="test", state="completed", parameters={"lr": 0.01})
        assert run.run_id == "run-1"
        assert run.experiment_name == "test"
        assert run.state == "completed"
        assert run.parameters == {"lr": 0.01}


class TestExperiment:
    def test_experiment_creation(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        assert exp.name == "test-exp"
        assert exp.experiment_id is not None
        assert exp.runs == {}

    def test_start_run(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run(parameters={"lr": 0.01})
        assert run.run_id in exp.runs
        assert exp.runs[run.run_id].parameters == {"lr": 0.01}

    def test_stop_run(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.stop_run(run.run_id)
        assert exp.runs[run.run_id].state == "completed"
        assert exp.runs[run.run_id].end_time is not None

    def test_log_metric(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_metric(run.run_id, "loss", 0.5)
        assert "loss" in exp.runs[run.run_id].metrics
        assert len(exp.runs[run.run_id].metrics["loss"]) == 1

    def test_log_metric_invalid_run(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        with pytest.raises(KeyError):
            exp.log_metric("bad-run-id", "loss", 0.5)

    def test_log_parameters(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_parameters(run.run_id, {"batch_size": 32})
        assert exp.runs[run.run_id].parameters == {"batch_size": 32}

    def test_log_artifact(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_artifact(run.run_id, "/tmp/model.pt", metadata={"epoch": 1})
        assert len(exp.runs[run.run_id].artifacts) == 1
        assert exp.runs[run.run_id].artifacts[0]["path"] == "/tmp/model.pt"

    def test_log_histogram(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_histogram(run.run_id, "weights", [0.1, 0.2, 0.3, 0.4, 0.5])
        assert "weights" in exp.runs[run.run_id].metrics
        assert exp.runs[run.run_id].metrics["weights"][0][0] == "histogram"

    def test_log_image(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_image(run.run_id, "samples", "/tmp/img.png")
        assert "samples" in exp.runs[run.run_id].metrics
        assert exp.runs[run.run_id].metrics["samples"][0] == ("image", "/tmp/img.png")

    def test_compare_runs(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run1 = exp.start_run()
        run2 = exp.start_run()
        exp.log_metric(run1.run_id, "loss", 0.5)
        exp.log_metric(run2.run_id, "loss", 0.3)
        comparison = exp.compare_runs([run1.run_id, run2.run_id], ["loss"])
        assert run1.run_id in comparison
        assert run2.run_id in comparison
        assert comparison[run1.run_id]["metrics"]["loss"]["last"] == 0.5

    def test_get_best_run(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run1 = exp.start_run()
        run2 = exp.start_run()
        exp.log_metric(run1.run_id, "loss", 0.5)
        exp.log_metric(run2.run_id, "loss", 0.2)
        exp.stop_run(run1.run_id)
        exp.stop_run(run2.run_id)
        best = exp.get_best_run("loss", mode="min")
        assert best.run_id == run2.run_id


class TestMetricStore:
    def test_log_and_get_scalar(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_scalar("run-1", "loss", 0.5)
        records = store.get("run-1", "loss")
        assert len(records) == 1
        assert records[0].value == 0.5
        assert records[0].metric_type == "scalar"

    def test_persistence(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_scalar("run-1", "loss", 0.5)
        store = MetricStore(tmp_storage)
        records = store.get("run-1", "loss")
        assert len(records) == 1

    def test_aggregate_scalar(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_scalar("run-1", "loss", 0.5)
        store.log_scalar("run-1", "loss", 0.3)
        agg = store.aggregate("run-1", "loss")
        assert agg is not None
        assert agg["mean"] == 0.4
        assert agg["min"] == 0.3
        assert agg["max"] == 0.5
        assert agg["last"] == 0.3
        assert agg["count"] == 2

    def test_aggregate_missing(self, tmp_storage):
        store = MetricStore(tmp_storage)
        assert store.aggregate("run-1", "loss") is None

    def test_log_histogram(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_histogram("run-1", "weights", [0.1, 0.2, 0.3])
        records = store.get("run-1", "weights")
        assert len(records) == 1
        assert records[0].metric_type == "histogram"
        assert records[0].value == [0.1, 0.2, 0.3]

    def test_log_image(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_image("run-1", "samples", "/tmp/img.png")
        records = store.get("run-1", "samples")
        assert len(records) == 1
        assert records[0].metric_type == "image"
        assert records[0].value == "/tmp/img.png"

    def test_get_all_run_ids(self, tmp_storage):
        store = MetricStore(tmp_storage)
        store.log_scalar("run-1", "loss", 0.5)
        store.log_scalar("run-2", "loss", 0.3)
        ids = store.get_all_run_ids()
        assert set(ids) == {"run-1", "run-2"}


class TestReportGenerator:
    def test_generate_html(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run = exp.start_run()
        exp.log_metric(run.run_id, "loss", 0.5)
        generator = ReportGenerator(exp)
        output_path = os.path.join(tmp_storage, "report.html")
        generator.generate_html(output_path)
        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Experiment Report" in content
        assert "test-exp" in content

    def test_compare_runs_markdown(self, tmp_storage):
        exp = Experiment(name="test-exp", storage_dir=tmp_storage)
        run1 = exp.start_run()
        run2 = exp.start_run()
        exp.log_metric(run1.run_id, "loss", 0.5)
        exp.log_metric(run2.run_id, "loss", 0.3)
        generator = ReportGenerator(exp)
        output_path = os.path.join(tmp_storage, "compare.md")
        generator.compare_runs([run1.run_id, run2.run_id], output_path)
        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Run Comparison" in content
