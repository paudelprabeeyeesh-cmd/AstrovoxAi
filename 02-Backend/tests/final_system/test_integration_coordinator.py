from final_system.integration_coordinator import IntegrationCoordinator, IntegrationStep, StepStatus


def test_run_sequential_steps():
    coordinator = IntegrationCoordinator()
    results_store = {}

    def step_a(**kw):
        results_store["a"] = "a"
        return "a"

    def step_b(**kw):
        results_store["b"] = "b"
        return "b"

    coordinator.register(IntegrationStep(name="a", fn=step_a))
    coordinator.register(IntegrationStep(name="b", fn=step_b, dependencies=["a"]))
    results = coordinator.run()
    assert results["a"].status == StepStatus.COMPLETED
    assert results["b"].status == StepStatus.COMPLETED
    assert results["b"].output == "b"


def test_skip_missing_dependency():
    coordinator = IntegrationCoordinator()
    coordinator.register(IntegrationStep(name="b", fn=lambda: None, dependencies=["a"]))
    results = coordinator.run()
    assert results["b"].status == StepStatus.SKIPPED


def test_failure_skips_dependents():
    coordinator = IntegrationCoordinator()

    def bad(**kw):
        raise RuntimeError("x")

    coordinator.register(IntegrationStep(name="a", fn=bad))
    coordinator.register(IntegrationStep(name="b", fn=lambda: None, dependencies=["a"]))
    results = coordinator.run()
    assert results["a"].status == StepStatus.FAILED
    assert results["b"].status == StepStatus.SKIPPED


def test_results_persisted():
    coordinator = IntegrationCoordinator()
    coordinator.register(IntegrationStep(name="a", fn=lambda: None))
    coordinator.run()
    assert coordinator.results()["a"].status == StepStatus.COMPLETED
