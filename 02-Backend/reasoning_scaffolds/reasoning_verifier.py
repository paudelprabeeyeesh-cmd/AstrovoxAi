from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class VerificationResult:
    step_index: int
    is_valid: bool
    message: str


def verify_reasoning_chain(
    steps: List[str],
    verify_step_fn: Callable[[int, str, List[str]], Optional[str]],
    context: Optional[List[str]] = None,
) -> List[VerificationResult]:
    context = context or []
    results: List[VerificationResult] = []
    for idx, step in enumerate(steps):
        message = verify_step_fn(idx, step, context[:idx]) or "OK"
        results.append(VerificationResult(step_index=idx, is_valid=message == "OK", message=message))
    return results


def verify_step(
    index: int,
    step: str,
    context: List[str],
    verify_fn: Callable[[int, str, List[str]], Optional[str]],
) -> Optional[VerificationResult]:
    message = verify_fn(index, step, context)
    if message is None:
        return VerificationResult(step_index=index, is_valid=True, message="OK")
    return VerificationResult(step_index=index, is_valid=False, message=message)


def chain_is_valid(results: List[VerificationResult]) -> bool:
    return all(r.is_valid for r in results)
