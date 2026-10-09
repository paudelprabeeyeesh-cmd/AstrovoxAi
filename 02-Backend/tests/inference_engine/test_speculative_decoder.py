import numpy as np

from inference_engine.speculative_decoder import (
    SpeculativeDecoder,
    DraftModel,
    TargetModel,
    softmax,
    log_softmax,
    rejection_sample,
)


def test_speculative_decoder_generate():
    decoder = SpeculativeDecoder(vocab_size=100, num_draft_tokens=2)
    tokens = decoder.generate(prompt_ids=[1, 2, 3], max_new_tokens=6)
    assert len(tokens) == 6


def test_speculative_decoder_generate_with_metrics():
    decoder = SpeculativeDecoder(vocab_size=100, num_draft_tokens=2)
    metrics = decoder.generate_with_metrics(prompt_ids=[1, 2, 3], max_new_tokens=6)
    assert metrics["total_tokens"] == 6
    assert metrics["accepted_tokens"] == 6
    assert 0.0 <= metrics["acceptance_rate"] <= 1.0


def test_speculative_decoder_vocab_size():
    decoder = SpeculativeDecoder(vocab_size=500, num_draft_tokens=3)
    assert decoder.vocab_size == 500
    assert decoder.num_draft_tokens == 3


def test_draft_model_forward():
    model = DraftModel(vocab_size=100, num_layers=2, hidden_size=64)
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    logits, kv = model.forward(input_ids)
    assert logits.shape[0] == 1
    assert logits.shape[1] == 3
    assert logits.shape[2] == 100


def test_target_model_forward():
    model = TargetModel(vocab_size=100, num_layers=4, hidden_size=128)
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    logits, kv = model.forward(input_ids)
    assert logits.shape[0] == 1
    assert logits.shape[1] == 3
    assert logits.shape[2] == 100


def test_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    probs = softmax(x)
    assert probs.shape == (1, 3)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_log_softmax():
    x = np.array([[1.0, 2.0, 3.0]])
    log_probs = log_softmax(x)
    assert log_probs.shape == (1, 3)
    probs = np.exp(log_probs)
    assert abs(probs.sum() - 1.0) < 1e-5


def test_rejection_sample():
    logits = np.array([0.1, 0.5, 0.4])
    token = rejection_sample(logits, draft_token=1, draft_prob=0.5)
    assert token in [0, 1, 2]


def test_rejection_sample_deterministic():
    logits = np.array([[0.1, 0.5, 0.4]])
    token = rejection_sample(logits, draft_token=1, draft_prob=0.5)
    assert token in [0, 1, 2]


def test_rejection_sample_accepts_draft():
    target_logits = np.array([[0.1, 10.0, 0.4]])
    token = rejection_sample(target_logits, draft_token=1, draft_prob=0.01)
    assert token == 1


def test_speculative_decoder_output_range():
    decoder = SpeculativeDecoder(vocab_size=100, num_draft_tokens=2)
    tokens = decoder.generate(prompt_ids=[0], max_new_tokens=5)
    for t in tokens:
        assert 0 <= t < 100


def test_draft_model_forward_with_kv():
    model = DraftModel(vocab_size=100, num_layers=2, hidden_size=64)
    input_ids = np.array([[1, 2, 3]], dtype=np.int64)
    logits, kv = model.forward(input_ids, past_kv={})
    assert kv == {}
