import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PropertyTestResult:
    name: str
    passed: bool
    sample_input: Any
    sample_output: Any
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class PropertySuiteResult:
    property_name: str
    samples: int
    passed: int
    failed: int
    duration_ms: float
    failures: List[PropertyTestResult] = field(default_factory=list)


class PropertyTester:
    def __init__(self, samples: int = 100):
        self.samples = samples

    def run(self, name: str, fn: Callable[[Any], Any], generator: Callable[[], Any]) -> PropertySuiteResult:
        failures: List[PropertyTestResult] = []
        passed = 0
        failed = 0
        total_duration = 0.0
        for _ in range(self.samples):
            sample = generator()
            start = _perf_counter()
            try:
                output = fn(sample)
                duration = (_perf_counter() - start) * 1000
                total_duration += duration
                passed += 1
            except Exception as exc:
                duration = (_perf_counter() - start) * 1000
                total_duration += duration
                failed += 1
                failures.append(PropertyTestResult(
                    name=name,
                    passed=False,
                    sample_input=sample,
                    sample_output=None,
                    error=str(exc),
                    duration_ms=duration,
                ))
        return PropertySuiteResult(
            property_name=name,
            samples=self.samples,
            passed=passed,
            failed=failed,
            duration_ms=round(total_duration, 3),
            failures=failures,
        )

    def summarize(self, result: PropertySuiteResult) -> Dict[str, Any]:
        return {
            "property": result.property_name,
            "samples": result.samples,
            "passed": result.passed,
            "failed": result.failed,
            "pass_rate": round(result.passed / max(result.samples, 1), 4),
            "duration_ms": result.duration_ms,
            "failure_count": len(result.failures),
        }


def _perf_counter() -> float:
    import time
    return time.perf_counter()
