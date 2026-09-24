import time
import pytest
from production_readiness.chaos_engineering import ChaosEngineer, ChaosRegistry, ChaosExperiment


def test_create_experiment():
    engineer = ChaosEngineer()
    exp = engineer.create_experiment("latency-test", "db", "latency", 10.0)
    assert exp.name == "latency-test"
    assert exp.status == "pending"


def test_run_experiment():
    engineer = ChaosEngineer()
    exp = engineer.create_experiment("latency-test", "db", "latency", 10.0)
    def dummy():
        return "ok"
    result = engineer.run_experiment(exp.id, dummy)
    assert result == "ok"
    assert exp.status == "completed"


def test_run_experiment_with_fault():
    engineer = ChaosEngineer()
    engineer.register_fault("latency", lambda func, params, *args, **kwargs: func(*args, **kwargs))
    exp = engineer.create_experiment("latency-test", "db", "latency", 10.0)
    def dummy():
        return "ok"
    result = engineer.run_experiment(exp.id, dummy)
    assert result == "ok"


def test_resilience_test():
    engineer = ChaosEngineer()
    engineer.register_fault("latency", lambda func, params, *args, **kwargs: func(*args, **kwargs))
    def dummy():
        return "ok"
    result = engineer.resilience_test(dummy, 3)
    assert result["total"] == 3
    assert result["passed"] == 3


def test_list_experiments():
    engineer = ChaosEngineer()
    engineer.create_experiment("latency-test", "db", "latency", 10.0)
    experiments = engineer.list_experiments()
    assert len(experiments) == 1


def test_experiment_registry():
    registry = ChaosRegistry()
    exp = ChaosExperiment(id="e1", name="n", target="t", fault_type="latency", duration_seconds=1.0)
    registry.register(exp)
    assert registry.get("e1") is exp
    assert len(registry.list()) == 1
