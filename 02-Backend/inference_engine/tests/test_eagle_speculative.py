
import pytest
import numpy as np

from inference_engine.eagle_speculative import (
    EAGLESpeculativeDecoder, EAGLEDraftModel, softmax
)


def test_eagle_draft_features():
    model = EAGLEDraftModel(vocab_size=100, hidden_size=64, feature_dim=32)
    hidden = np.random.randn(1, 8, 64).astype(np.float32)
    features = model.extract_features(hidden)
    assert features.shape == (1, 8, 32)


def test_eagle_draft_forward():
    model = EAGLEDraftModel(vocab_size=100, hidden_size=64, feature_dim=32)
    hidden = np.random.randn(1, 1, 64).astype(np.float32)
    logits = model.draft_forward(hidden)
    assert logits.shape[-1] == 100


def test_eagle_generate_draft_tokens():
    model = EAGLEDraftModel(vocab_size=100, hidden_size=64, feature_dim=32)
    hidden = np.random.randn(1, 1, 64).astype(np.float32)
    tokens = model.generate_draft_tokens(hidden, num_tokens=5)
    assert len(tokens) == 5
    for t in tokens:
        assert 0 <= t < 100


def test_eagle_speculative_decoder():
    decoder = EAGLESpeculativeDecoder(vocab_size=100, num_draft_tokens=4)
    tokens, metrics = decoder.speculative_generate(prompt_ids=[1, 2, 3], max_new_tokens=8)
    assert len(tokens) == 8
    assert "draft_tokens" in metrics
    assert "accepted" in metrics
    assert "rejected" in metrics


def test_eagle_draft_step():
    decoder = EAGLESpeculativeDecoder(vocab_size=100, num_draft_tokens=4)
    hidden = np.random.randn(1, 1, 128).astype(np.float32)
    tokens, features = decoder.draft_step(hidden)
    assert len(tokens) == 4
    assert features.shape[-1] == 64


def test_eagle_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    probs = softmax(x)
    assert abs(probs.sum() - 1.0) < 1e-5
    assert probs.shape == (1, 3)
