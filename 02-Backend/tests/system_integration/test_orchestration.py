import pytest
from system_integration.orchestration import (
    DAG,
    DAGExecutor,
    Task,
    TaskResult,
    TaskStatus,
    WorkflowEngine,
)


def test_dag_topological_sort():
    results = []
    def job(name): return name
    dag = DAG(tasks=[
        Task(name="a", fn=job, deps=[]),
        Task(name="b", fn=job, deps=["a"]),
        Task(name="c", fn=job, deps=["a"]),
        Task(name="d", fn=job, deps=["b", "c"]),
    ])
    ex = DAGExecutor(dag)
    order = ex._topological_sort()
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("d")


def test_dag_execute_all():
    executed = {}
    def job(name): executed[name] = name; return name
    dag = DAG(tasks=[
        Task(name="a", fn=job, deps=[]),
        Task(name="b", fn=job, deps=["a"]),
    ])
    ex = DAGExecutor(dag)
    ex.execute()
    assert executed["a"] == "a"
    assert executed["b"] == "b"


def test_dag_skips_on_missing_dep():
    dag = DAG(tasks=[Task(name="a", fn=lambda: None, deps=["b"])])
    ex = DAGExecutor(dag)
    ex.execute()
    assert ex._results["a"].status == TaskStatus.SKIPPED


def test_dag_retry_on_failure():
    calls = {"n": 0}
    def flaky(): calls["n"] += 1; raise RuntimeError("x")
    dag = DAG(tasks=[Task(name="a", fn=flaky, retries=1)])
    ex = DAGExecutor(dag)
    ex.execute()
    assert ex._results["a"].status == TaskStatus.FAILED
    assert calls["n"] == 2


def test_workflow_engine_run():
    executed = {}
    def job(name): executed[name] = name
    engine = WorkflowEngine()
    engine.register(DAG(tasks=[
        Task(name="a", fn=job, deps=[]),
        Task(name="b", fn=job, deps=["a"]),
    ], name="w1"))
    res = engine.run("w1")
    assert all(r.status == TaskStatus.COMPLETED for r in res.values())
    assert executed["a"] == "a"
    assert executed["b"] == "b"


def test_dag_executor_status():
    dag = DAG(tasks=[Task(name="a", fn=lambda: None, deps=[])])
    ex = DAGExecutor(dag)
    ex.execute()
    assert ex.status()["a"] == TaskStatus.COMPLETED
