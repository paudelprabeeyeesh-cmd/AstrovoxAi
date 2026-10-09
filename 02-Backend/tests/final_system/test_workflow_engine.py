import pytest
from final_system.workflow_engine import Pipeline, Stage, StageStatus, WorkflowEngine


def test_pipeline_run_all():
    engine = WorkflowEngine()
    executed = {}
    def job(name): executed[name] = name; return name
    pipeline = Pipeline(name="p1", stages=[
        Stage(name="a", fn=job),
        Stage(name="b", fn=job),
    ])
    engine.register(pipeline)
    results = engine.run("p1")
    assert results["a"].status == StageStatus.COMPLETED
    assert results["b"].status == StageStatus.COMPLETED


def test_pipeline_skip_on_condition():
    engine = WorkflowEngine()
    pipeline = Pipeline(name="p2", stages=[
        Stage(name="a", fn=lambda: None, condition=lambda: False),
    ])
    engine.register(pipeline)
    results = engine.run("p2")
    assert results["a"].status == StageStatus.SKIPPED


def test_pipeline_stop_on_failure():
    engine = WorkflowEngine()
    def bad(): raise RuntimeError("x")
    pipeline = Pipeline(name="p3", stages=[
        Stage(name="a", fn=bad),
        Stage(name="b", fn=lambda: None),
    ])
    engine.register(pipeline)
    results = engine.run("p3")
    assert results["a"].status == StageStatus.FAILED
    assert "b" not in results


def test_results_persisted():
    engine = WorkflowEngine()
    pipeline = Pipeline(name="p4", stages=[Stage(name="a", fn=lambda **kw: None)])
    engine.register(pipeline)
    engine.run("p4")
    assert engine.results("p4")["a"].status == StageStatus.COMPLETED


def test_unknown_pipeline():
    engine = WorkflowEngine()
    with pytest.raises(KeyError):
        engine.run("missing")
