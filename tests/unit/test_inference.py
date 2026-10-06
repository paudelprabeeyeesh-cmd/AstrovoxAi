"""Tests for streaming inference utilities."""

from __future__ import annotations

import numpy as np
import pytest

from astrovox.inference import GenerationConfig, TokenStream, batch_generate, sample_logits


def test_sample_logits_returns_int():
    logits = np.array([0.1, 0.2, 0.7], dtype=np.float32)
    token = sample_logits(logits, temperature=1.0)
    assert isinstance(token, int)
    assert 0 <= token < 3


def test_sample_logits_greedy_when_temperature_zero():
    logits = np.array([0.1, 0.2, 0.7], dtype=np.float32)
    token = sample_logits(logits, temperature=0.0)
    assert token == 2


def test_token_stream_limits_by_stop():
    stream = TokenStream(tokens=[1, 2, 3], config=GenerationConfig(stop=["3"]))
    collected = list(stream)
    assert len(collected) <= 3


def test_batch_generate_returns_lists():
    def fake_model(x):
        return np.zeros((1, 1, 4), dtype=np.float32)

    prompts = [np.ones((1, 2), dtype=np.int64), np.ones((1, 2), dtype=np.int64)]
    results = batch_generate(fake_model, prompts, GenerationConfig(max_new_tokens=2))
    assert len(results) == 2
