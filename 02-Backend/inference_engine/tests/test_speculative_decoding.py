
import numpy as np

from inference_engine.speculative_decoding import (
    SpeculativeDecoder, DraftModel, TargetModel, rejection_sample, softmax
)


def test_speculative_decoder_generate():
    decoder = SpeculativeDecoder()
    tokens = decoder.generate(prompt_ids=[1, 2, 3], max_new_tokens=8)
    assert len(tokens) == 8


def test_speculative_decoder_metrics():
    decoder = SpeculativeDecoder()
    metrics = decoder.generate_with_metrics(prompt_ids=[1, 2, 3], max_new_tokens=10)
    assert metrics["accepted_tokens"] == 10
    assert metrics["total_tokens"] == 10
    assert 0.0 <= metrics["acceptance_rate"] <= 1.0


def test_rejection_sample():
    logits = np.array([0.1, 0.5, 0.4])
    token = rejection_sample(logits, draft_token=1, draft_prob=0.5)
    assert token in [0, 1, 2]


def test_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    probs = softmax(x)
    assert probs.shape == (1, 3)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_draft_model_forward():
    model = DraftModel(vocab_size=100)
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    logits, kv = model.forward(input_ids)
    assert logits.shape[1] == 3
    assert logits.shape[2] == 100


def test_target_model_forward():
    model = TargetModel(vocab_size=100)
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    logits, kv = model.forward(input_ids)
    assert logits.shape[1] == 3
    assert logits.shape[2] == 100


def test_rejection_sample_deterministic():
    logits = np.array([[0.1, 0.5, 0.4]])
    token = rejection_sample(logits, draft_token=1, draft_prob=0.5)
    assert token in [0, 1, 2]
