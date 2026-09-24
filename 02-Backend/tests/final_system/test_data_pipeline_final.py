import pytest
from final_system.data_pipeline_final import DataPipeline, ETLJob, PipelineResult


def test_etl_run_success():
    pipeline = DataPipeline()
    job = ETLJob(
        name="sales",
        extract=lambda: [1, 2, 3],
        transform=lambda data, **kw: [x * 2 for x in data],
        load=lambda data, **kw: sum(data),
    )
    pipeline.register(job)
    result = pipeline.run("sales")
    assert result.success is True
    assert result.extracted == [1, 2, 3]
    assert result.transformed == [2, 4, 6]
    assert result.loaded == 12


def test_etl_missing_job():
    pipeline = DataPipeline()
    result = pipeline.run("missing")
    assert result.success is False
    assert "not found" in result.error


def test_etl_transform_failure():
    pipeline = DataPipeline()
    def bad_transform(data, **kw): raise RuntimeError("bad")
    job = ETLJob(name="t1", extract=lambda: None, transform=bad_transform, load=lambda x: x)
    pipeline.register(job)
    result = pipeline.run("t1")
    assert result.success is False
    assert "bad" in result.error


def test_etl_result_persisted():
    pipeline = DataPipeline()
    job = ETLJob(name="t2", extract=lambda: None, transform=lambda x: x, load=lambda x: x)
    pipeline.register(job)
    pipeline.run("t2")
    stored = pipeline.result("t2")
    assert stored is not None
    assert stored.success is True
