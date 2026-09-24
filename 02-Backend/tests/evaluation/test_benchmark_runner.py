from evaluation.benchmark_runner import BenchmarkRunner, BenchmarkTask, BenchmarkResult


def test_benchmark_runner_register_and_run():
    runner = BenchmarkRunner()
    task = BenchmarkTask(name="fast", func=lambda: None, repeats=3)
    runner.register(task)
    results = runner.run()
    assert "fast" in results
    assert isinstance(results["fast"], BenchmarkResult)
    assert len(results["fast"].times) == 3


def test_benchmark_result_stats():
    result = BenchmarkResult(name="r", times=[0.1, 0.2, 0.3])
    assert abs(result.mean - 0.2) < 1e-9
    assert abs(result.median - 0.2) < 1e-9
    assert result.min == 0.1
    assert result.max == 0.3


def test_benchmark_result_empty():
    result = BenchmarkResult(name="r")
    assert result.mean == 0.0
    assert result.median == 0.0
    assert result.min == 0.0
    assert result.max == 0.0


def test_benchmark_runner_run_specific():
    runner = BenchmarkRunner()
    runner.register(BenchmarkTask(name="a", func=lambda: None))
    runner.register(BenchmarkTask(name="b", func=lambda: None))
    runner.run(name="a")
    assert runner.get_result("a") is not None
    assert runner.get_result("b") is None


def test_benchmark_result_to_dict():
    result = BenchmarkResult(name="r", times=[0.1, 0.2])
    d = result.to_dict()
    assert d["name"] == "r"
    assert abs(d["mean"] - 0.15) < 1e-9
    assert "times" in d
