import functools
import json
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class OptimizationReport:
    original: float
    optimized: float
    improvement_ms: float
    improvement_share: float


def _make_context(registry: Dict[str, float], name: str) -> Dict[str, Any]:
    return {"registry": registry, "name": name}


def make_cache_key(name: str, args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> str:
    return f"{name}:{args}:{sorted(kwargs.items())}"


def memoize(registry: Dict[str, Any], name: str) -> Callable:
    cache: Dict[str, Any] = {}

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            key = make_cache_key(name, args, kwargs)
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        return wrapped

    return decorator


def batch_invoke(
    registry: Dict[str, float],
    name: str,
    func: Callable,
    items: List[Any],
    batch_size: int,
    delay: float,
) -> List[Any]:
    results = []
    for start in range(0, len(items), batch_size):
        batch = items[start: start + batch_size]
        results.extend(func(item) for item in batch)
        if delay:
            time.sleep(delay)
    return results


def backoff_wait(attempt: int, base: float, cap: float, factor: float) -> float:
    wait = min(base * (factor ** attempt), cap)
    wait += random.uniform(0, 0.01)
    return wait


def apply_backoff(registry: Dict[str, float], name: str, attempt: int) -> None:
    wait = backoff_wait(attempt, base=0.05, cap=1.0, factor=2.0)
    time.sleep(wait)


def tune_batch_size(
    registry: Dict[str, float],
    name: str,
    min_size: int,
    max_size: int,
) -> int:
    return min_size + random.randint(0, max(0, max_size - min_size))


def run_optimized(
    registry: Dict[str, float],
    name: str,
    func: Callable,
    items: List[Any],
) -> OptimizationReport:
    start = time.perf_counter()
    results = batch_invoke(
        registry, name, func, items, batch_size=min(8, len(items)), delay=0.0
    )
    optimized = time.perf_counter() - start
    registry[name] = optimized
    return OptimizationReport(
        original=registry.get(name + "_original", optimized),
        optimized=optimized,
        improvement_ms=(registry.get(name + "_original", optimized) - optimized) * 1000.0,
        improvement_share=(registry.get(name + "_original", optimized) - optimized) / registry.get(name + "_original", optimized) if registry.get(name + "_original", optimized) else 0.0,
    )


def tune_with_backoff(
    registry: Dict[str, float], name: str, func: Callable
) -> Optional[Exception]:
    last_exc = None
    for attempt in range(4):
        try:
            registry[name] = time.perf_counter()
            func()
            registry[name] = time.perf_counter() - registry.get(name, 0.0)
            return None
        except Exception as exc:
            last_exc = exc
            apply_backoff(registry, name, attempt)
    return last_exc


def optimize(
    registry: Dict[str, float],
    name: str,
    func: Callable,
    items: List[Any],
) -> OptimizationReport:
    original_name = name + "_original"
    registry[original_name] = time.perf_counter()
    results = [func(item) for item in items]
    original = time.perf_counter() - registry.get(original_name, time.perf_counter())
    registry[original_name] = original
    report = run_optimized(registry, name, func, items)
    return OptimizationReport(
        original=original,
        optimized=report.optimized,
        improvement_ms=(original - report.optimized) * 1000.0,
        improvement_share=(original - report.optimized) / original if original else 0.0,
    )


def to_json(report: OptimizationReport) -> str:
    return json.dumps(
        {
            "original": report.original,
            "optimized": report.optimized,
            "improvement_ms": report.improvement_ms,
            "improvement_share": report.improvement_share,
        }
    )
