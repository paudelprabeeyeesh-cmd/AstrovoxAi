import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

_retrainer_spec = importlib.util.spec_from_file_location(
    "models.llm.continuous.retrainer", os.path.join(ROOT, "models", "llm", "continuous", "retrainer.py")
)
_retrainer_mod = importlib.util.module_from_spec(_retrainer_spec)
_retrainer_spec.loader.exec_module(_retrainer_mod)

RetrainingConfig = _retrainer_mod.RetrainingConfig
DataCollector = _retrainer_mod.DataCollector
QualityMonitor = _retrainer_mod.QualityMonitor
DeploymentManager = _retrainer_mod.DeploymentManager
ContinuousRetrainer = _retrainer_mod.ContinuousRetrainer


class TestDataCollector:
    def test_collect_creates_file(self, tmp_path):
        collector = DataCollector(str(tmp_path / "data"))
        path = collector.collect([{"text": "hello"}, {"text": "world"}])
        assert path.exists()
        assert path.suffix == ".jsonl"

    def test_collect_empty(self, tmp_path):
        collector = DataCollector(str(tmp_path / "data"))
        path = collector.collect([])
        assert path.exists()

    def test_count_total(self, tmp_path):
        collector = DataCollector(str(tmp_path / "data"))
        collector.collect([{"text": "a"}] * 5)
        assert collector.count_total() == 5

    def test_count_multiple_files(self, tmp_path):
        collector = DataCollector(str(tmp_path / "data"))
        collector.collect([{"text": "a"}])
        collector.collect([{"text": "b"}])
        assert collector.count_total() == 2


class TestQualityMonitor:
    def test_evaluate_without_previous(self):
        monitor = QualityMonitor()
        report = monitor.evaluate("/tmp/model", {"quality_score": 0.8})
        assert report.score == 0.8
        assert report.previous_score is None
        assert report.passed is True

    def test_evaluate_with_previous(self):
        monitor = QualityMonitor()
        monitor.evaluate("/tmp/model", {"quality_score": 0.8})
        report = monitor.evaluate("/tmp/model", {"quality_score": 0.85})
        assert report.previous_score == 0.8
        assert report.score == 0.85
        assert report.passed is True

    def test_evaluate_drop_triggers_failure(self):
        monitor = QualityMonitor()
        monitor.evaluate("/tmp/model", {"quality_score": 0.9})
        report = monitor.evaluate("/tmp/model", {"quality_score": 0.8})
        assert report.passed is False

    def test_should_rollback(self):
        monitor = QualityMonitor()
        monitor.evaluate("/tmp/model", {"quality_score": 0.9})
        report = monitor.evaluate("/tmp/model", {"quality_score": 0.8})
        assert monitor.should_rollback(report, threshold=0.05) is True
        assert monitor.should_rollback(report, threshold=0.15) is False


class TestDeploymentManager:
    def test_deploy_creates_version(self, tmp_path):
        manager = DeploymentManager(str(tmp_path / "deploy"), max_retention=5)
        source = tmp_path / "source_model"
        source.mkdir()
        (source / "model.bin").write_text("data")
        target = manager.deploy(str(source), "v1")
        assert target.exists()
        assert (target / "model.bin").exists()

    def test_deploy_creates_multiple_versions(self, tmp_path):
        manager = DeploymentManager(str(tmp_path / "deploy"), max_retention=3)
        source = tmp_path / "source_model"
        source.mkdir()
        (source / "model.bin").write_text("data")
        manager.deploy(str(source), "v1")
        manager.deploy(str(source), "v2")
        manager.deploy(str(source), "v3")
        versions = sorted((tmp_path / "deploy").iterdir())
        assert len(versions) == 3

    def test_rollback_returns_previous(self, tmp_path):
        manager = DeploymentManager(str(tmp_path / "deploy"), max_retention=5)
        source = tmp_path / "source_model"
        source.mkdir()
        (source / "model.bin").write_text("data")
        manager.deploy(str(source), "v1")
        manager.deploy(str(source), "v2")
        rollback = manager.rollback("v2")
        assert rollback is not None
        assert rollback.name == "v1"

    def test_prune_old_versions(self, tmp_path):
        manager = DeploymentManager(str(tmp_path / "deploy"), max_retention=2)
        source = tmp_path / "source_model"
        source.mkdir()
        (source / "model.bin").write_text("data")
        for v in ["v1", "v2", "v3", "v4"]:
            manager.deploy(str(source), v)
        versions = sorted((tmp_path / "deploy").iterdir())
        assert len(versions) == 2


class TestContinuousRetrainer:
    def test_ingest_and_count(self, tmp_path):
        config = RetrainingConfig(
            model_path=str(tmp_path / "model"),
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            min_new_samples=1,
            trigger_interval_hours=0,
        )
        retrainer = ContinuousRetrainer(config)
        count = retrainer.ingest([{"text": "sample1"}])
        assert count == 1
        assert retrainer.data_collector.count_total() == 1

    def test_record_metric(self, tmp_path):
        config = RetrainingConfig(
            model_path=str(tmp_path / "model"),
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            metrics_path=str(tmp_path / "metrics.jsonl"),
        )
        retrainer = ContinuousRetrainer(config)
        retrainer.record_metric({"event": "test", "value": 1.0})
        assert config.metrics_path.endswith(".jsonl")
        assert Path(config.metrics_path).exists()

    def test_should_trigger(self, tmp_path):
        config = RetrainingConfig(
            model_path=str(tmp_path / "model"),
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            min_new_samples=2,
            trigger_interval_hours=0,
        )
        retrainer = ContinuousRetrainer(config)
        retrainer.ingest([{"text": "a"}])
        assert retrainer.should_trigger() is False
        retrainer.ingest([{"text": "b"}])
        assert retrainer.should_trigger() is True

    def test_train_triggers_deploy(self, tmp_path):
        config = RetrainingConfig(
            model_path=str(tmp_path / "model"),
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            min_new_samples=1,
            trigger_interval_hours=0,
        )
        retrainer = ContinuousRetrainer(config)
        retrainer.ingest([{"text": "a"}])

        def fake_train(model_path: str, data_dir: str) -> dict[str, Any]:
            return {"quality_score": 0.9}

        report = retrainer.train(fake_train)
        assert report.passed is True
        assert retrainer._current_version.startswith("v")
        versions = list(Path(config.output_dir).iterdir())
        assert len(versions) == 1

    def test_train_triggers_rollback_on_quality_drop(self, tmp_path):
        config = RetrainingConfig(
            model_path=str(tmp_path / "model"),
            data_dir=str(tmp_path / "data"),
            output_dir=str(tmp_path / "output"),
            min_new_samples=1,
            trigger_interval_hours=0,
            rollback_threshold=0.05,
        )
        retrainer = ContinuousRetrainer(config)
        retrainer.ingest([{"text": "a"}])

        def fake_train(model_path: str, data_dir: str) -> dict[str, Any]:
            return {"quality_score": 0.5}

        report = retrainer.train(fake_train)
        assert report.passed is False
