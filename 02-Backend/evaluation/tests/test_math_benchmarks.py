
from app.evaluation.math_benchmarks import MathBenchmarks


def _runner(prompt: str) -> str:
    if "2 + 2" in prompt:
        return "4"
    if "15 * 8" in prompt:
        return "120"
    if "2x + 4 = 10" in prompt:
        return "3"
    if "square root of 144" in prompt:
        return "12"
    if "20% of 50" in prompt:
        return "10"
    return "0"


def test_math_benchmark_run():
    bench = MathBenchmarks()
    result = bench.run_benchmark(_runner)
    assert result["benchmark"] == "math"
    assert result["total"] == 5
    assert result["passed"] >= 4
