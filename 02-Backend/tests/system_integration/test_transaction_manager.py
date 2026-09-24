import pytest
from system_integration.transaction_manager import (
    DistributedTransaction,
    Saga,
    SagaOrchestrator,
    SagaStep,
    TransactionManager,
)


def test_transaction_manager_begin():
    tm = TransactionManager()
    tx = tm.begin("t1", ["p1"])
    assert tx.tx_id == "t1"


def test_transaction_commit():
    tm = TransactionManager()
    tx = tm.begin("t1", ["p1"])
    tm.register_action("t1", "p1", lambda: None, lambda: None)
    assert tm.commit("t1") is True
    assert tm._transactions["t1"].state.name == "COMMITTED"


def test_transaction_rollback_on_failure():
    tm = TransactionManager()
    tx = tm.begin("t1", ["p1"])
    tm.register_action("t1", "p1", lambda: (_ for _ in ()).throw(RuntimeError("boom")), lambda: None)
    assert tm.commit("t1") is False
    assert tm._transactions["t1"].state.name == "FAILED"


def test_saga_orchestrator_execute():
    orch = SagaOrchestrator()
    steps = [SagaStep(name="s1", execute=lambda: 1, compensate=lambda: None)]
    saga = orch.create("saga1", steps)
    result = orch.execute("saga1")
    assert result.state.name == "COMPLETED"
    assert result.executed == ["s1"]


def test_saga_compensate_on_failure():
    orch = SagaOrchestrator()
    steps = [SagaStep(name="s1", execute=lambda: (_ for _ in ()).throw(RuntimeError()), compensate=lambda: None)]
    saga = orch.create("saga1", steps)
    result = orch.execute("saga1")
    assert result.state.name == "ROLLED_BACK"
    assert result.compensated == ["s1"]


def test_saga_get():
    orch = SagaOrchestrator()
    orch.create("s1", [])
    assert orch.get("s1") is not None
    assert orch.get("x") is None
