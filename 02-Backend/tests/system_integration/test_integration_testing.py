import pytest
from system_integration.integration_testing import (
    E2ERunner,
    IntegrationTester,
    TestResult,
    TestScenario,
)


def test_integration_tester_success():
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: None, lambda: None]))
    results = tester.run_all()
    assert results["s1"].passed is True
    assert results["s1"].steps_passed == 2


def test_integration_tester_failure():
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: (_ for _ in ()).throw(AssertionError("boom"))]))
    results = tester.run_all()
    assert results["s1"].passed is False
    assert results["s1"].steps_failed == 1


def test_e2e_runner_summary():
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: None]))
    runner = E2ERunner(tester)
    out = runner.run()
    assert out["summary"]["total"] == 1
    assert out["summary"]["passed"] == 1
    assert out["summary"]["failed"] == 0


def test_teardown_runs_on_success():
    teardown = []
    def td(): teardown.append(1)
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: None], teardowns=[td]))
    tester.run_all()
    assert teardown == [1]


def test_teardown_runs_on_failure():
    teardown = []
    def td(): teardown.append(1)
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: (_ for _ in ()).throw(RuntimeError())], teardowns=[td]))
    tester.run_all()
    assert teardown == [1]


def test_tester_results():
    tester = IntegrationTester()
    tester.register(TestScenario(name="s1", steps=[lambda: None]))
    tester.run_all()
    assert tester.summary()["total"] >= 1
