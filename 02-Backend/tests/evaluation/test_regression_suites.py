from evaluation.regression_suites import BenchmarkResult, RegressionRecord, RegressionSuite, BenchmarkRegistry


def test_benchmark_result_to_dict():
    result = BenchmarkResult(name="bench1", score=0.95, metadata={"version": "1.0"})
    d = result.to_dict()
    assert d["name"] == "bench1"
    assert d["score"] == 0.95
    assert d["metadata"] == {"version": "1.0"}
    assert "timestamp" in d


def test_regression_suite_add_result():
    suite = RegressionSuite(name="suite1")
    result = BenchmarkResult(name="bench1", score=0.9)
    suite.add_result(result)
    assert len(suite._history) == 1


def test_regression_suite_set_and_get_baseline():
    suite = RegressionSuite(name="suite1")
    suite.set_baseline("bench1", 1.0)
    assert suite.get_baseline("bench1") == 1.0
    assert suite.get_baseline("missing") is None


def test_regression_suite_check_regression_no_baseline():
    suite = RegressionSuite(name="suite1", threshold=0.05)
    record = suite.check_regression("bench1", 0.9)
    assert record.is_regression is False
    assert record.delta == 0.0
    assert suite.get_baseline("bench1") == 0.9


def test_regression_suite_check_regression_detected():
    suite = RegressionSuite(name="suite1", threshold=0.05)
    suite.set_baseline("bench1", 1.0)
    record = suite.check_regression("bench1", 0.9)
    assert record.is_regression is True
    assert abs(record.delta - 0.1) < 1e-9
    assert record.benchmark_name == "bench1"
    assert record.baseline_score == 1.0
    assert record.current_score == 0.9


def test_regression_suite_check_no_regression():
    suite = RegressionSuite(name="suite1", threshold=0.05)
    suite.set_baseline("bench1", 1.0)
    record = suite.check_regression("bench1", 0.99)
    assert record.is_regression is False


def test_regression_suite_run_suite():
    suite = RegressionSuite(name="suite1", threshold=0.05)
    suite.set_baseline("a", 1.0)
    suite.set_baseline("b", 1.0)
    records = suite.run_suite({"a": 0.9, "b": 0.99})
    assert len(records) == 2
    assert records[0].is_regression is True
    assert records[1].is_regression is False


def test_regression_suite_has_regression():
    suite = RegressionSuite(name="suite1", threshold=0.05)
    suite.set_baseline("a", 1.0)
    assert suite.has_regression({"a": 0.9}) is True
    assert suite.has_regression({"a": 1.0}) is False


def test_regression_suite_get_history():
    suite = RegressionSuite(name="suite1")
    suite.add_result(BenchmarkResult(name="bench1", score=1.0))
    suite.add_result(BenchmarkResult(name="bench2", score=0.8))
    suite.add_result(BenchmarkResult(name="bench1", score=0.9))
    history = suite.get_history("bench1")
    assert len(history) == 2
    assert history[0].score == 1.0
    assert history[1].score == 0.9


def test_regression_suite_export_report():
    suite = RegressionSuite(name="suite1", threshold=0.1)
    suite.set_baseline("bench1", 1.0)
    suite.add_result(BenchmarkResult(name="bench1", score=0.9))
    report = suite.export_report()
    assert report["suite"] == "suite1"
    assert report["threshold"] == 0.1
    assert report["baselines"] == {"bench1": 1.0}
    assert report["history_count"] == 1


def test_benchmark_registry_singleton():
    registry1 = BenchmarkRegistry()
    registry2 = BenchmarkRegistry()
    assert registry1 is registry2


def test_benchmark_registry_register_and_get_suite():
    registry = BenchmarkRegistry()
    registry._suites.clear()
    suite = registry.register_suite("suite1", threshold=0.05)
    assert registry.get_suite("suite1") is suite
    assert registry.list_suites() == ["suite1"]


def test_benchmark_registry_evaluate_all():
    registry = BenchmarkRegistry()
    registry._suites.clear()
    suite = registry.register_suite("suite1", threshold=0.05)
    suite.set_baseline("a", 1.0)
    results = {
        "suite1": {"a": 0.9},
        "missing": {"a": 0.9},
    }
    all_records = registry.evaluate_all(results)
    assert "suite1" in all_records
    assert "missing" not in all_records
    assert all_records["suite1"][0].is_regression is True
