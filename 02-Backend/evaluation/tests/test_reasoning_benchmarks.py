
from app.evaluation.reasoning_benchmarks import ReasoningBenchmarks


def _runner(prompt: str) -> str:
    if "valid" in prompt.lower():
        return "Yes, this is valid."
    if "tomorrow" in prompt.lower():
        return "Yes"
    if "wet" in prompt.lower():
        return "Rain"
    if "drop" in prompt.lower():
        return "Gravity"
    if "fish" in prompt.lower():
        return "No"
    return "Unknown"


def test_reasoning_benchmark_run():
    bench = ReasoningBenchmarks()
    result = bench.run_benchmark(_runner)
    assert result["benchmark"] == "reasoning"
    assert result["total"] == 5
    assert result["passed"] >= 3
