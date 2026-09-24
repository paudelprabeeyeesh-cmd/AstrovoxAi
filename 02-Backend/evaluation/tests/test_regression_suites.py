from evaluation.regression_suites import RegressionSuite, RegressionRecord, BenchmarkResult, BenchmarkRegistry


def test_regression_suite_check_no_baseline():
    suite = RegressionSuite(name="s1")
    record = suite.check_regression("b1", 0.9)
    assert isinstance(record, RegressionRecord)
    assert record.is_regression is False


def test_regression_suite_check_regression():
    suite = RegressionSuite(name="s1", threshold=0.05)
    suite.set_baseline("b1", 1.0)
    record = suite.check_regression("b1", 0.9)
    assert record.is_regression is True
    assert abs(record.delta - 0.1) < 1e-9


def test_regression_suite_run_suite():
    suite = RegressionSuite(name="s1")
    records = suite.run_suite({"b1": 1.0, "b2": 0.8})
    assert len(records) == 2
    assert all(isinstance(r, RegressionRecord) for r in records)


def test_regression_suite_has_regression():
    suite = RegressionSuite(name="s1", threshold=0.05)
    suite.set_baseline("b1", 1.0)
    assert suite.has_regression({"b1": 0.9}) is True
    assert suite.has_regression({"b1": 1.0}) is False


def test_regression_suite_export_report():
    suite = RegressionSuite(name="s1")
    report = suite.export_report()
    assert report["suite"] == "s1"
    assert report["history_count"] == 0


def test_benchmark_registry():
    registry = BenchmarkRegistry()
    registry.register_suite("s1")
    assert registry.list_suites() == ["s1"]
    suite = registry.get_suite("s1")
    assert suite is not None
