from __future__ import annotations

from typing import List, Optional

import pytest

from reasoning_scaffolds.reasoning_verifier import (
    VerificationResult,
    verify_reasoning_chain,
    verify_step,
    chain_is_valid,
)


def test_verify_reasoning_chain_all_valid():
    steps = ["step1", "step2"]

    def verify_fn(index: int, step: str, context: list[str]) -> Optional[str]:
        return None

    results = verify_reasoning_chain(steps, verify_fn)
    assert all(r.is_valid for r in results)


def test_verify_reasoning_chain_some_invalid():
    steps = ["step1", "bad"]

    def verify_fn(index: int, step: str, context: list[str]) -> Optional[str]:
        return "invalid" if step == "bad" else None

    results = verify_reasoning_chain(steps, verify_fn)
    assert results[0].is_valid
    assert not results[1].is_valid
    assert results[1].message == "invalid"


def test_verify_step_valid():
    def verify_fn(index: int, step: str, context: list[str]) -> Optional[str]:
        return None

    result = verify_step(0, "step", [], verify_fn)
    assert result is not None
    assert result.is_valid


def test_verify_step_invalid():
    def verify_fn(index: int, step: str, context: list[str]) -> Optional[str]:
        return "error"

    result = verify_step(0, "step", [], verify_fn)
    assert result is not None
    assert not result.is_valid


def test_chain_is_valid():
    results = [
        VerificationResult(0, True, ""),
        VerificationResult(1, True, ""),
    ]
    assert chain_is_valid(results) is True

    results_invalid = [
        VerificationResult(0, True, ""),
        VerificationResult(1, False, "err"),
    ]
    assert chain_is_valid(results_invalid) is False
