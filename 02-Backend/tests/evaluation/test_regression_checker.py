from evaluation.regression_checker import RegressionChecker, RegressionRecord


def test_regression_checker_no_baseline():
    checker = RegressionChecker()
    record = checker.check("metric", 0.9)
    assert record.is_regression is False
    assert record.delta == 0.0


def test_regression_checker_regression():
    checker = RegressionChecker(threshold=0.05)
    checker.set_baseline("metric", 1.0)
    record = checker.check("metric", 0.9)
    assert record.is_regression is True
    assert abs(record.delta - 0.1) < 1e-9


def test_regression_checker_no_regression():
    checker = RegressionChecker(threshold=0.05)
    checker.set_baseline("metric", 1.0)
    record = checker.check("metric", 0.99)
    assert record.is_regression is False


def test_regression_checker_suite():
    checker = RegressionChecker(threshold=0.05)
    checker.set_baseline("a", 1.0)
    checker.set_baseline("b", 1.0)
    records = checker.check_suite({"a": 0.9, "b": 0.99})
    assert len(records) == 2
    assert records[0].is_regression is True
    assert records[1].is_regression is False


def test_regression_checker_has_regression():
    checker = RegressionChecker(threshold=0.05)
    checker.set_baseline("a", 1.0)
    assert checker.has_regression({"a": 0.9}) is True
    assert checker.has_regression({"a": 1.0}) is False


def test_regression_checker_history():
    checker = RegressionChecker()
    checker.check("m", 1.0)
    checker.check("m", 0.9)
    history = checker.history("m")
    assert len(history) == 2
    assert history == [1.0, 0.9]
